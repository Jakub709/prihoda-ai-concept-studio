"""Background Blender execution. No shell; only a fixed, trusted generator is run."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from .schemas import Project
from .config import setting, data_root

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=data_root(ROOT)/'output'
OUTPUT.mkdir(parents=True,exist_ok=True)
POOL=ThreadPoolExecutor(max_workers=1)
LOCK=threading.Lock()
JOBS={}
GENERATOR=ROOT/'blender'/'generate_scene.py'

def find_blender():
    configured=setting('BLENDER_PATH')
    if configured:
        p=Path(configured.strip('"')).expanduser()
        return str(p.resolve()) if p.is_file() else None
    command=shutil.which('blender')
    if command: return command
    portable=ROOT.parent/'.tools'
    candidates=list(portable.glob('blender-*/blender.exe'))+list(Path('C:/Program Files/Blender Foundation').glob('Blender*/blender.exe'))
    for p in candidates:
        if p.is_file(): return str(p.resolve())
    for p in ['/Applications/Blender.app/Contents/MacOS/Blender','/usr/bin/blender','/snap/bin/blender']:
        if Path(p).is_file(): return p
    return None

def job_key(project,render):
    # A generator edit invalidates the output cache.
    payload=project.model_dump_json()+GENERATOR.read_text(encoding='utf-8-sig')+str(render)+setting('BLENDER_RENDER_ENGINE','BLENDER_EEVEE_NEXT')
    return hashlib.sha256(payload.encode()).hexdigest()[:20]

def output_result(key,render):
    return {'id':key,'state':'ready','stage':'Ready',
            'model_url':f'/output/{key}/model.glb',
            'manifest_url':f'/output/{key}/manifest.json',
            'blend_url':f'/output/{key}/scene.blend',
            'preview_url':f'/output/{key}/preview.png' if render else None}

def save_current(project):
    current=data_root(ROOT)/'projects'/'current_project.json'
    current.parent.mkdir(parents=True,exist_ok=True)
    temp=current.with_suffix('.tmp')
    temp.write_text(project.model_dump_json(indent=2),encoding='utf-8')
    temp.replace(current)

def generate(project:Project,render=False):
    executable=find_blender()
    if not executable: raise RuntimeError('Blender could not be found. Set BLENDER_PATH in the application environment, or use the demo preview.')
    key=job_key(project,render)
    with LOCK:
        if key in JOBS and JOBS[key]['state']!='error':
            if JOBS[key]['state']=='ready': save_current(project)
            return JOBS[key].copy()
        required=['scene.blend','model.glb','manifest.json']+(['preview.png'] if render else [])
        folder=OUTPUT/key
        if all((folder/name).is_file() for name in required):
            try:
                manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
                if manifest['project']==project.model_dump() and len(manifest['ducts'])==project.ducts.count:
                    JOBS[key]=output_result(key,render)
                    save_current(project)
                    return JOBS[key].copy()
            except (OSError,ValueError,KeyError): pass
        JOBS[key]={'id':key,'state':'queued','stage':'Waiting for 3D engine'}
    def work():
        folder=OUTPUT/key
        try:
            folder.mkdir(exist_ok=True)
            jobfile=folder/'project.json'
            jobfile.write_text(project.model_dump_json(indent=2),encoding='utf-8')
            JOBS[key].update(state='running',stage='Generating geometry')
            command=[executable,'--background','--factory-startup','--python-exit-code','1','--python',str(GENERATOR),'--','--project',str(jobfile),'--output',str(folder)]
            if render: command.append('--render')
            environment=os.environ.copy()
            environment['BLENDER_RENDER_ENGINE']=setting('BLENDER_RENDER_ENGINE','BLENDER_EEVEE_NEXT')
            with (folder/'blender.log').open('w',encoding='utf-8') as log:
                completed=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=600 if render else 150,
                    env=environment,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            required=['scene.blend','model.glb','manifest.json']+(['preview.png'] if render else [])
            if completed.returncode or any(not (folder/name).is_file() for name in required):
                raise RuntimeError('The 3D engine could not finish the export. Your previous concept is preserved. Try again, or use the demo preview.')
            # Read actual scene measurements, not only the input project.
            manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
            if len(manifest['ducts'])!=project.ducts.count:
                raise RuntimeError('Generated geometry could not be verified. Your previous concept is preserved.')
            with LOCK:
                save_current(project)
                JOBS[key].update(output_result(key,render))
        except subprocess.TimeoutExpired:
            JOBS[key].update(state='error',stage='Generation timed out',error='Blender took too long. Reduce scene complexity and try again. The previous concept is preserved.')
        except Exception as exc:
            message=str(exc) if isinstance(exc,RuntimeError) else 'The 3D engine could not generate this concept. Check the Blender configuration and try again.'
            JOBS[key].update(state='error',stage='Generation failed',error=message)
    POOL.submit(work)
    return JOBS[key].copy()

def get_job(key):
    with LOCK:
        job=JOBS.get(key)
        if not job: return None
        result=job.copy()
    if result['state']=='running':
        try:
            result['stage']=json.loads((OUTPUT/key/'progress.json').read_text())['stage']
        except (OSError,ValueError,KeyError): pass
    return result
