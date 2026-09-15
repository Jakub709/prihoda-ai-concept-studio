"""Run after connecting real services. Saves a labelled QA project in Supabase.

No mocks, secret logging, or fallback database. Kept as a reviewable cloud
acceptance record rather than deleting customer database records automatically.
"""
import json,sys,time,urllib.error
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests.e2e import api,generate,ROOT
from backend.app.network import tls_context
from backend.app import storage
expected_current=None

def main():
    global expected_current
    checks=api('/connections/test',{})
    if not all(checks.get(k,{}).get('connected') for k in ('openai','supabase')):
        print(json.dumps({'result':'NOT_CONNECTED','connections':checks},indent=2))
        raise SystemExit(2)
    print('Live OpenAI and Supabase connections verified.',flush=True)
    bucket=storage.call('GET','/storage/v1/bucket/'+storage.BUCKET)
    assert bucket['public'] is False, 'The project bucket must be private.'
    parsed=api('/parse',{'text':'Production hall 30 x 15 x 6 m, airflow 7000 m3/h, two white circular ducts, diameter 600 mm, 22 m long, installed 4.5 m above the floor. Supply temperature 16 C, room temperature 22 C. Large nozzles angled 30 degrees downward.'})
    assert parsed['provider']=='openai' and parsed['receipt']['request_id']
    assert parsed['project']['air']['airflow_m3h']==7000
    assert parsed['project']['air']['static_pressure_pa'] is None
    assert parsed['project']['distribution']['angle_deg']==30
    original=api('/demo')
    original['project_name']='Studio connection check '+time.strftime('%Y-%m-%d %H:%M:%S')
    response=api('/modify',{'command':'Použij tři červená potrubí, posuň je o metr výš a natoč trysky 35° dolů.','project':original})
    assert response['receipt']['provider']=='openai' and response['receipt']['request_id']
    changed=response['project']
    assert (changed['ducts']['count'],changed['ducts']['color'],changed['ducts']['installation_height_m'],changed['distribution']['angle_deg'])==(3,'#d71920',5.5,35)
    print('Live AI extraction and Czech modification verified. Generating Blender render...',flush=True)
    expected_current=changed
    model=generate(changed,True)
    saved=api('/projects',{'project':changed,'model_id':model['id'],'note':'Live OpenAI + Supabase acceptance test'})
    restored=api('/projects/'+saved['project_id'])
    assert restored['project']==changed
    assert restored['version']==1
    versions=api('/projects/'+saved['project_id']+'/versions')
    assert len(versions)==1
    print('Supabase version 1 saved and restored. Checking version history...',flush=True)
    second=json.loads(json.dumps(changed))
    second['visualization']['show_dimensions']=False
    saved_second=api('/projects',{'project':second,'model_id':model['id'],'project_id':saved['project_id'],'expected_version':1,'note':'Live acceptance: second version, dimensions hidden'})
    assert saved_second['version']==2
    latest=api('/projects/'+saved['project_id'])
    historical=api('/projects/'+saved['project_id']+'?version=1')
    assert latest['project']==second and latest['version']==2
    assert historical['project']==changed and historical['version']==1
    assert [v['version'] for v in api('/projects/'+saved['project_id']+'/versions')]==[2,1]
    assert any(p['id']==saved['project_id'] and p['latest_version']==2 for p in api('/projects'))
    import httpx
    assets={}
    for name in ('model_url','manifest_url','blend_url','preview_url'):
        result=httpx.get(restored['model'][name],timeout=45,verify=tls_context())
        result.raise_for_status()
        assert len(result.content)>100
        assets[name]=len(result.content)
    report={'result':'PASS','checked_at':time.strftime('%Y-%m-%d %H:%M:%S'),'connections':checks,'extraction_receipt':parsed['receipt'],'receipt':response['receipt'],'saved':saved_second,'history_versions':[2,1],'historical_parameters_match':True,'private_bucket':True,'private_assets_downloaded':assets,'blender_seconds':model['seconds']}
    (ROOT/'output/live-acceptance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    current=ROOT/'projects/current_project.json'
    original_current=current.read_bytes() if current.exists() else None
    try:main()
    except urllib.error.HTTPError as exc:
        print(json.dumps({'result':'FAIL','http_status':exc.code,'detail':exc.read().decode('utf-8')},ensure_ascii=False))
        raise SystemExit(1)
    finally:
        if original_current is not None and current.exists() and expected_current is not None:
            if json.loads(current.read_text(encoding='utf-8'))==expected_current:
                current.write_bytes(original_current)
