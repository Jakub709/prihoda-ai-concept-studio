"""Supabase Postgres + private object storage. No simulated cloud saves."""
import json
import re
from uuid import UUID, uuid4
from urllib.parse import urlparse
import httpx
from .config import setting, ROOT, data_root
from .schemas import Project
from .network import tls_context

BUCKET = 'prihoda-concepts'

class StorageError(RuntimeError):
    pass

def connection():
    url = setting('SUPABASE_URL').rstrip('/')
    key = setting('SUPABASE_SECRET_KEY') or setting('SUPABASE_SERVICE_ROLE_KEY')
    if not url or not key:
        raise StorageError('Connect a Supabase project in Connections to save and open projects.')
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not re.fullmatch(r'[a-z0-9-]+\.supabase\.co', parsed.netloc):
        raise StorageError('Use your HTTPS Supabase project URL (https://project-ref.supabase.co).')
    headers = {'apikey': key}
    if key.startswith('eyJ'):
        headers['Authorization'] = 'Bearer ' + key
    return url, headers

def call(method, path, **kwargs):
    url, headers = connection()
    headers.update(kwargs.pop('headers', {}))
    try:
        response = httpx.request(method, url + path, headers=headers, timeout=40, verify=tls_context(), **kwargs)
    except httpx.HTTPError:
        raise StorageError('Supabase could not be reached. Check the connection and try again.') from None
    if response.status_code >= 400:
        try: code = response.json().get('code', '')
        except ValueError: code = ''
        if response.status_code in (401, 403):
            raise StorageError('Supabase rejected the server key. Check your secret key and database permissions.')
        if code in ('PGRST205', '42P01', 'PGRST202'):
            raise StorageError('Supabase is reachable. Run the supplied database migration to create the project library.')
        if code == '40001':
            raise StorageError('A newer version was saved elsewhere. Reopen the project before saving your changes.')
        raise StorageError(f'Supabase could not complete this operation (HTTP {response.status_code}). Your local concept is preserved.')
    return response.json() if response.content else None

def health():
    call('GET', '/rest/v1/prihoda_projects', params={'select':'id', 'limit':'1'})
    call('GET', '/storage/v1/bucket/' + BUCKET)
    return {'connected': True, 'message': 'Live connection verified · Postgres + private storage'}

def list_projects():
    return call('GET', '/rest/v1/prihoda_project_library', params={'select':'*','order':'updated_at.desc','limit':'60'})

def project_versions(project_id):
    project_id = str(UUID(project_id))
    return call('GET', '/rest/v1/prihoda_versions', params={'project_id':'eq.'+project_id,'select':'id,version,note,created_at','order':'version.desc'})

def load_project(project_id, version=None):
    project_id = str(UUID(project_id))
    params = {'project_id':'eq.'+project_id,'select':'*','order':'version.desc','limit':'1'}
    if version is not None: params['version'] = 'eq.'+str(version)
    rows = call('GET', '/rest/v1/prihoda_versions', params=params)
    if not rows: raise StorageError('This project version could not be found.')
    row = rows[0]
    parameters = Project.model_validate(row['parameters']).model_dump()
    library = call('GET', '/rest/v1/prihoda_projects', params={'id':'eq.'+project_id,'select':'latest_version'})
    model = {'id':row['id']}
    url, _ = connection()
    for name, path in row['assets'].items():
        if name not in ('model_url','manifest_url','blend_url','preview_url') or not re.fullmatch(re.escape(project_id)+r'/[a-f0-9]{32}/[a-zA-Z0-9_.-]+',path):
            raise StorageError('This saved version contains an invalid asset reference.')
        result = call('POST', '/storage/v1/object/sign/'+BUCKET+'/'+path, json={'expiresIn':3600})
        signed=result['signedURL']
        model[name] = signed if signed.startswith(url+'/storage/v1/') else url+'/storage/v1'+signed
    return {'project':parameters, 'model':model, 'project_id':project_id,
            'version':row['version'], 'latest_version':library[0]['latest_version']}

def save_project(project, model_id, project_id=None, expected_version=0, note='', preview_name=None):
    connection()
    project_id = str(UUID(project_id)) if project_id else str(uuid4())
    if not re.fullmatch(r'[a-f0-9]{20}|demo', model_id):
        raise StorageError('Generate this concept locally before saving a new version.')
    folder = data_root(ROOT)/'output'/model_id
    try:
        manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        # Visualization switches do not alter geometry and are stored with this version.
        source = Project.model_validate(manifest['project']).model_dump(exclude={'visualization','project_name','original_request'})
        if source != project.model_dump(exclude={'visualization','project_name','original_request'}):
            raise StorageError('Generate your changed parameters before saving this version.')
    except (OSError, ValueError, KeyError):
        raise StorageError('The generated model is missing. Generate the concept again before saving.') from None
    files = {'model_url':(folder/'model.glb','model/gltf-binary'),
             'manifest_url':(folder/'manifest.json','application/json'),
             'blend_url':(folder/'scene.blend','application/octet-stream')}
    if preview_name:
        if not re.fullmatch(r'prihoda-concept-[a-f0-9]{12}\.png', preview_name):
            raise StorageError('The preview filename is invalid.')
        files['preview_url'] = (data_root(ROOT)/'output'/'exports'/preview_name, 'image/png')
    elif (folder/'preview.png').is_file(): files['preview_url'] = (folder/'preview.png','image/png')
    if any(not path.is_file() for path, _ in files.values()):
        raise StorageError('Some 3D files are missing. Generate the concept again before saving.')
    prefix = project_id+'/'+uuid4().hex
    assets = {}
    try:
        for name, (path, mime) in files.items():
            remote = prefix+'/'+path.name
            call('POST', '/storage/v1/object/'+BUCKET+'/'+remote, content=path.read_bytes(), headers={'Content-Type':mime})
            assets[name] = remote
        return call('POST', '/rest/v1/rpc/save_prihoda_version', json={
            'p_id':project_id, 'p_name':project.project_name, 'p_expected':expected_version,
            'p_parameters':project.model_dump(), 'p_assets':assets, 'p_note':note[:1000]})
    except StorageError:
        # A timed-out RPC may already have committed. Preserve uploaded assets;
        # deleting them here could destroy a successfully saved version.
        raise
