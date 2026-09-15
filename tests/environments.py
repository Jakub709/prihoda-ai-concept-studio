"""Verify the selected room type changes exported Blender geometry."""
import copy,json,struct
from tests.e2e import api,generate,ROOT

def main():
    original=api('/demo');report=[]
    try:
        for kind,material in [('warehouse','Corrugated cardboard'),('sports_hall','Sports court | maple')]:
            project=copy.deepcopy(original);project['room']['type']=kind
            print('Generating '+kind,flush=True)
            job=generate(project,False)
            raw=(ROOT/'output'/job['id']/'model.glb').read_bytes()
            size=struct.unpack_from('<I',raw,12)[0];gltf=json.loads(raw[20:20+size])
            material_index=next(i for i,m in enumerate(gltf['materials']) if m['name']==material)
            geometry=[p for mesh in gltf['meshes'] for p in mesh['primitives'] if p.get('material')==material_index]
            assert geometry,'Expected room-specific geometry was not exported'
            for node in gltf['nodes']:
                if node.get('name','').startswith('Duct_'):
                    assert 'TEXCOORD_0' in gltf['meshes'][node['mesh']]['primitives'][0]['attributes']
            report.append({'room':kind,'job':job,'verified_material':material,'geometry_primitives':len(geometry)})
    finally:generate(original,False)
    (ROOT/'output/environments-report.json').write_text(json.dumps({'result':'PASS','environments':report},indent=2),encoding='utf-8')
    print('PASS: warehouse and sports hall contain distinct geometry and textile UVs.',flush=True)

if __name__=='__main__':main()
