"""Real Blender audits for the secondary profile and distribution choices."""
import copy,json
from tests.e2e import api,generate,audit,ROOT

def main():
    original=api('/demo');results=[]
    cases=[('semicircular','perforation','horizontal'),
           ('semicircular','microperforation','downward'),
           ('circular','small_nozzles','angled_down'),
           ('circular','large_nozzles','downward')]
    try:
        for i,(shape,kind,direction) in enumerate(cases):
            project=copy.deepcopy(original)
            project['ducts'].update(count=1,shape=shape,diameter_mm=800,length_m=18,installation_height_m=4,spacing_m=3)
            project['distribution'].update(type=kind,direction=direction,angle_deg=40)
            print('Checking '+shape+' / '+kind+' / '+direction,flush=True)
            job=generate(project,False)
            geometry=audit(job,project,'variant-'+str(i+1))
            results.append({'shape':shape,'distribution':kind,'direction':direction,'job':job,'geometry':geometry})
    finally:
        generate(original,False)
    report={'result':'PASS','variants':results}
    (ROOT/'output/variants-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('PASS: all four variants verified in actual Blender scenes.',flush=True)

if __name__=='__main__':main()
