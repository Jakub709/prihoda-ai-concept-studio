import json, math, sys, argparse
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser()
p.add_argument('--count',type=int,required=True)
p.add_argument('--height',type=float,required=True)
p.add_argument('--diameter',type=float,required=True)
p.add_argument('--angle',type=float,required=True)
p.add_argument('--color',required=True)
p.add_argument('--shape',default='circular',choices=['circular','semicircular'])
p.add_argument('--report',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
bpy.context.view_layer.update()
ducts=[o for o in bpy.data.objects if o.name.startswith('Duct_')]
assert len(ducts)==a.count,('count',len(ducts))
for o in ducts:
    assert abs(o.location.z-a.height)<.001,('height',o.location.z)
    # Object.dimensions follows local axes. Measure transformed mesh vertices.
    world=[o.matrix_world @ v.co for v in o.data.vertices]
    dimensions=[max(v[i] for v in world)-min(v[i] for v in world) for i in range(3)]
    assert abs(dimensions[1]-a.diameter/1000)<.001,('diameter',dimensions)
    expected_depth=a.diameter/(2000 if a.shape=='semicircular' else 1000)
    assert abs(dimensions[2]-expected_depth)<.001,('profile',dimensions)
    c=o.data.materials[0].node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value
    expected=tuple((int(a.color[i:i+2],16)/255)**2.2 for i in (1,3,5))
    assert all(abs(c[i]-expected[i])<.0001 for i in range(3)),('material',list(c))
nozzles=[o for o in bpy.data.objects if o.name.startswith('Distribution nozzle')]
assert nozzles
for o in nozzles:
    vec=o.matrix_world.to_quaternion()@Vector((0,0,1))
    actual=math.degrees(math.asin(min(1,abs(vec.z))))
    assert abs(actual-a.angle)<.01,('nozzle angle',actual)
paths=[o for o in bpy.data.objects if o.name.startswith('Airflow_line')]
assert paths
for o in paths:
    spline=o.data.splines[0]
    if a.angle==0:
        assert abs(spline.points[1].co.z-spline.points[0].co.z)<.001
    else:
        assert spline.points[1].co.z<spline.points[0].co.z
report={'result':'PASS','scene':bpy.data.filepath,'actual_duct_count':len(ducts),'actual_height_m':ducts[0].location.z,'actual_diameter_mm':round(ducts[0].dimensions.y*1000),'color':a.color,'actual_nozzle_angle_deg':a.angle,'nozzles':len(nozzles),'airflow_paths':len(paths)}
Path(a.report).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('GEOMETRY_AUDIT '+json.dumps(report),flush=True)
