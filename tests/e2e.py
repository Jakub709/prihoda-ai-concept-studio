"""Exercise the running frontend proxy, API, Blender output, patch and undo."""
import argparse,json,struct,time,subprocess,os
from pathlib import Path
import urllib.request
from backend.app.services import find_blender
ROOT=Path(__file__).resolve().parents[1]
BASE=os.environ.get('STUDIO_TEST_URL','http://127.0.0.1:5173').rstrip('/')
COMMAND='Use three red ducts, move them one metre higher and point the nozzles 35 degrees downward.'
def api(path,data=None):
    body=None if data is None else json.dumps(data).encode()
    req=urllib.request.Request(BASE+'/api'+path,data=body,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=180 if path.startswith(('/projects','/connections/test')) else 45) as r:return json.loads(r.read())
def generate(project,render):
    start=time.monotonic()
    job=api('/generate'+('?render=true' if render else ''),project)
    deadline=start+(620 if render else 165)
    while job['state']!='ready':
        if job['state']=='error':raise RuntimeError(job['error'])
        if time.monotonic()>deadline:raise RuntimeError('Generation timeout')
        time.sleep(.3);job=api('/jobs/'+job['id'])
    job['seconds']=round(time.monotonic()-start,2)
    folder=ROOT/'output'/job['id']
    for name in ['scene.blend','model.glb','manifest.json']+(['preview.png'] if render else []):
        assert (folder/name).stat().st_size>100
    raw=(folder/'model.glb').read_bytes()
    magic,version,size=struct.unpack_from('<III',raw)
    assert magic==0x46546c67 and version==2 and size==len(raw)
    length,kind=struct.unpack_from('<II',raw,12)
    gltf=json.loads(raw[20:20+length])
    nodes=[n for n in gltf['nodes'] if n.get('name','').startswith('Duct_')]
    assert len(nodes)==project['ducts']['count']
    return job
def audit(job,project,label):
    d=project['ducts'];dist=project['distribution']
    report=ROOT/'output'/(label+'-audit.json')
    angle=0 if dist['direction']=='horizontal' else 90 if dist['direction']=='downward' else dist['angle_deg']
    result=subprocess.run([find_blender(),'--background',str(ROOT/'output'/job['id']/'scene.blend'),'--python-exit-code','1','--python',str(ROOT/'tests/audit_scene.py'),'--','--count',str(d['count']),'--height',str(d['installation_height_m']),'--diameter',str(d['diameter_mm']),'--shape',d['shape'],'--angle',str(angle),'--color',d['color'],'--report',str(report)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45)
    assert result.returncode==0,result.stdout[-2000:]+result.stderr[-1000:]
    return json.loads(report.read_text())
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--render',action='store_true');args=parser.parse_args()
    assert api('/status')['blender_ready']
    with urllib.request.urlopen(BASE,timeout=5) as r:assert 'AI Concept Studio' in r.read().decode()
    parsed=api('/parse',{'text':'We have a production hall 30 × 15 × 6 m. Required airflow is 7,000 m³/h. We are considering two circular fabric ducts, diameter 600 mm, 22 m long, installed 4.5 m above the floor. Supply temperature 16 °C, room temperature 22 °C. Use large nozzles angled 30° downward.'})
    assert parsed['project']['air']['airflow_m3h']==7000
    assert parsed['project']['air']['static_pressure_pa'] is None
    original=api('/demo')
    print('Generating initial model...',flush=True)
    before=generate(original,args.render)
    before_audit=audit(before,original,'initial')
    modification=api('/modify',{'command':COMMAND,'project':original})
    changed=modification['project']
    assert len(modification['changes'])==4
    assert (changed['ducts']['count'],changed['ducts']['installation_height_m'],changed['ducts']['color'],changed['distribution']['angle_deg'])==(3,5.5,'#d71920',35)
    print('Generating modified model...',flush=True)
    after=generate(changed,args.render)
    after_audit=audit(after,changed,'modified')
    print('Restoring original project...',flush=True)
    restored=generate(original,args.render)
    saved=json.loads((ROOT/'projects/current_project.json').read_text())
    assert saved==original
    assert restored['id']==before['id']
    report={'result':'PASS','checked_at':time.strftime('%Y-%m-%d %H:%M:%S'),'request_extraction':len(parsed['extracted']),'before':before,'after':after,'undo_restored_json':True,'before_geometry':before_audit,'after_geometry':after_audit}
    (ROOT/'output/e2e-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
