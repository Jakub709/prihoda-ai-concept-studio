"""Stable deterministic generator. User instructions can change JSON, never this code."""
import argparse, json, math, os, sys
from pathlib import Path
import bpy
from mathutils import Vector
parser=argparse.ArgumentParser()
parser.add_argument('--project',required=True)
parser.add_argument('--output',required=True)
parser.add_argument('--render',action='store_true')
options=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
project=json.loads(Path(options.project).read_text(encoding='utf-8-sig'))
out=Path(options.output).resolve()
out.mkdir(parents=True,exist_ok=True)

def status(message):
    (out/'progress.json').write_text(json.dumps({'stage':message}),encoding='utf-8')
    print(message,flush=True)

def rgb(h):
    h=h.lstrip('#')
    return tuple((int(h[i:i+2],16)/255)**2.2 for i in (0,2,4))

def material(name,color,roughness=.85,alpha=1):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,alpha)
    m.use_nodes=True
    n=m.node_tree.nodes.get('Principled BSDF')
    n.inputs['Base Color'].default_value=(*color,1)
    n.inputs['Roughness'].default_value=roughness
    n.inputs['Alpha'].default_value=alpha
    if alpha<1: m.surface_render_method='DITHERED'
    return m

def box(name,loc,size,mat,bevel=0):
    # Direct data creation avoids a dependency-graph update for every primitive.
    sx,sy,sz=(v/2 for v in size)
    verts=[(-sx,-sy,-sz),(-sx,-sy,sz),(-sx,sy,-sz),(-sx,sy,sz),
           (sx,-sy,-sz),(sx,-sy,sz),(sx,sy,-sz),(sx,sy,sz)]
    faces=[(0,2,6,4),(1,5,7,3),(0,4,5,1),(2,3,7,6),(0,1,3,2),(4,6,7,5)]
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    o=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(o)
    o.location=loc
    o.data.materials.append(mat)
    if bevel:
        mod=o.modifiers.new('Soft industrial edges','BEVEL')
        mod.width=bevel
        mod.segments=2
        o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    return o

def cylinder(name,start,end,radius,mat,vertices=20):
    start,end=Vector(start),Vector(end)
    v=end-start
    verts=[(radius*math.cos(2*math.pi*j/vertices),radius*math.sin(2*math.pi*j/vertices),z)
           for z in (-v.length/2,v.length/2) for j in range(vertices)]
    faces=[(j,(j+1)%vertices,(j+1)%vertices+vertices,j+vertices) for j in range(vertices)]
    faces.extend([tuple(range(vertices-1,-1,-1)),tuple(range(vertices,2*vertices))])
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    o=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(o)
    o.location=(start+end)/2
    o.rotation_mode='QUATERNION'
    o.rotation_quaternion=v.to_track_quat('Z','Y')
    o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth=len(p.vertices)==4
    if name.startswith('Duct_'):
        uv=mesh.uv_layers.new(name='Textile weave UV')
        for p in mesh.polygons:
            if p.index<vertices:
                j=p.index
                coords=[(j/vertices*2*math.pi*radius/0.16,0),((j+1)/vertices*2*math.pi*radius/0.16,0),((j+1)/vertices*2*math.pi*radius/0.16,v.length/.16),(j/vertices*2*math.pi*radius/0.16,v.length/.16)]
                for loop,co in zip(p.loop_indices,coords): uv.data[loop].uv=co
            else:
                for loop in p.loop_indices:
                    co=mesh.vertices[mesh.loops[loop].vertex_index].co
                    uv.data[loop].uv=(co.x/.16,co.y/.16)
    return o

def path(name,points,mat,width=.012):
    curve=bpy.data.curves.new(name,'CURVE')
    curve.dimensions='3D'
    curve.resolution_u=10
    curve.bevel_depth=width
    curve.bevel_resolution=1
    spline=curve.splines.new('POLY')
    spline.points.add(len(points)-1)
    for p,co in zip(spline.points,points): p.co=(*co,1)
    o=bpy.data.objects.new(name,curve)
    bpy.context.collection.objects.link(o)
    curve.materials.append(mat)
    return o

def figure(x,y):
    c=material('Scale figure charcoal',rgb('#5e6b75'))
    cylinder('Scale figure torso',(x,y,.76),(x,y,1.37),.15,c,12)
    cylinder('Scale figure left leg',(x-.09,y,.05),(x-.09,y,.83),.065,c,10)
    cylinder('Scale figure right leg',(x+.09,y,.05),(x+.09,y,.83),.065,c,10)
    cylinder('Scale figure left arm',(x-.23,y,.82),(x-.18,y,1.33),.052,c,10)
    cylinder('Scale figure right arm',(x+.23,y,.82),(x+.18,y,1.33),.052,c,10)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=.135,location=(x,y,1.57))
    bpy.context.object.name='Scale figure head'
    bpy.context.object.data.materials.append(c)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
status('Generating geometry')
r,d,dist=project['room'],project['ducts'],project['distribution']
L,W,H=r['length_m'],r['width_m'],r['height_m']
concrete=material('Concrete | matte',rgb('#515b64'),.69)
walls=material('Painted walls',rgb('#8d9ba4'))
steel=material('Structure | powder coated',rgb('#394953'),.38)
dark=material('Machine graphite',rgb('#253743'),.44)
light=material('Machine panels',rgb('#ccd3d6'),.48)
glass=material('Window blue grey',rgb('#173c4d'),.18)
yellow=material('Safety markings',rgb('#e3b958'),.7)
red=material('Equipment accent',rgb('#b83b40'))
wire=material('Suspension wire',rgb('#687986'),.6)
fabric=material('Fabric textile',rgb(d['color']),.96)
nodes=fabric.node_tree.nodes
# A real tiled tangent-space normal texture survives the GLB export.
texture=bpy.data.images.new('Woven polyester normal',width=128,height=128)
texture.colorspace_settings.name='Non-Color'
pixels=[]
for py in range(128):
    for px in range(128):
        nx=.28*math.sin(px*2*math.pi/8)*(1+.2*math.cos(py*2*math.pi/16))
        ny=.28*math.sin(py*2*math.pi/8)*(1+.2*math.cos(px*2*math.pi/16))
        nz=math.sqrt(max(.1,1-nx*nx-ny*ny))
        pixels.extend((nx*.5+.5,ny*.5+.5,nz*.5+.5,1))
texture.pixels.foreach_set(pixels)
texture.filepath_raw=str(out/'textile-normal.png');texture.file_format='PNG';texture.save();texture.pack()
tex=nodes.new('ShaderNodeTexImage');tex.image=texture
normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.4
fabric.node_tree.links.new(tex.outputs['Color'],normal.inputs['Color'])
fabric.node_tree.links.new(normal.outputs['Normal'],nodes.get('Principled BSDF').inputs['Normal'])
nodes.get('Principled BSDF').inputs['Sheen Weight'].default_value=.3
nodes.get('Principled BSDF').inputs['Sheen Tint'].default_value=(*rgb(d['color']),1)
seam=material('Textile seams',tuple(max(.01,c*.79) for c in rgb(d['color'])),.97)
airmat=material('Illustrative airflow',rgb('#6fa7be'),.7,.65)
zone=material('Occupied zone | 1.8 m',rgb('#b2d0de'),1,.035)
zoneedge=material('Occupied zone boundary',rgb('#85b3c8'),1,.4)
box('Hall floor',(0,0,-.14),(L+.4,W+.4,.28),concrete,.08)
box('Back wall plinth',(0,W/2,.7),(L,.16,1.4),walls)
box('End wall plinth',(-L/2,0,.7),(.16,W,1.4),walls)
# Repeated structure and windows give scale without hiding the installation.
bays=max(2,min(8,round(L/6)))
for i in range(bays+1):
    x=-L/2+L*i/bays
    for y in (-W/2,W/2):
        box('Structural column',(x,y,H/2),(.22,.24,H),steel,.025)
        box('Column base',(x,y,.08),(.48,.5,.16),dark)
    if i%2==0:
        box('Roof cross member',(x,0,H-.12),(.13,W,.20),steel)
    if i<bays:
        mid=x+L/bays/2
        box('Window panel',(mid,W/2,H*.65),(L/bays-.3,.08,H*.39),glass)
        box('Window horizontal rail',(mid,W/2-.06,H*.65),(L/bays-.3,.045,.04),steel)
box('Back eave',(0,W/2,H-.1),(L,.2,.2),steel)
box('Front eave',(0,-W/2,H-.1),(L,.2,.2),steel)
for x in range(-int(L/2)+3,int(L/2),6):
    box('Floor joint',(x,0,.006),(.018,W,.008),steel)
if r['type']=='production_hall':
    for side in (-1,1):
        y=side*W*.33
        for x in (-L*.28,0,L*.28):
            box('Machine footprint',(x,y,.04),(2.5,2,.08),dark,.06)
            box('Machine body',(x,y,.7),(1.9,1.5,1.25),light,.07)
            box('Machine enclosure',(x-.2,y,1.5),(1.2,1.25,.8),dark,.06)
            box('Machine window',(x-.2,y-.635,1.53),(.86,.015,.43),glass,.02)
            box('Machine control',(x+.72,y-.78,1.18),(.27,.15,.48),dark,.02)
            box('Control screen',(x+.72,y-.865,1.28),(.18,.01,.16),glass)
            cylinder('Status lamp',(x+.72,y,1.35),(x+.72,y,1.58),.04,red,10)
            for xx in (-1.43,1.43):
                box('Floor safety marking',(x+xx,y,.011),(.055,2.45,.012),yellow)
            for yy in (-1.225,1.225):
                box('Floor safety marking',(x,y+yy,.011),(2.92,.055,.012),yellow)
if r['type']!='sports_hall':
    # Pallet rack along far end.
    for side in (-1,1):
        ry=side*W*.29
        for dx in (-.5,.5):
            for dy in (-1.1,1.1):
                box('Rack upright',(-L*.43+dx,ry+dy,1.4),(.08,.08,2.8),steel)
        for z in (.18,1.3,2.4):
            box('Rack shelf',(-L*.43,ry,z),(1.1,2.4,.09),yellow)
            box('Stored pallet',(-L*.43,ry,z+.32),(.86,1.9,.55),light,.025)
figure(L*.11,-W*.06)
figure(-L*.29,-W*.11)

# Architectural detail is exported as geometry, including fasteners, trusses,
# machine interfaces, skirting, duct supports and the presentation plinth.
ivory=material('Architectural white',rgb('#e1e5e5'),.6)
rubber=material('Rubber and gaskets',rgb('#141d22'),.94)
alloy=material('Brushed aluminium',rgb('#a1afb5'),.27)
alloy.node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value=.78
led=material('LED | neutral white',rgb('#d5edf0'),.35)
led.node_tree.nodes.get('Principled BSDF').inputs['Emission Color'].default_value=(*rgb('#c4e6f2'),1)
led.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value=3
screen=material('Control display | cyan',rgb('#2388a7'),.3)
screen.node_tree.nodes.get('Principled BSDF').inputs['Emission Color'].default_value=(*rgb('#248da6'),1)
screen.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value=1.4
wood=material('Pallet wood',rgb('#a18b6a'))
def lettering(body,loc,size,mat,rotation=(math.pi/2,0,0),name='Hall lettering'):
    data=bpy.data.curves.new(name,'FONT');data.body=body;data.size=size;data.extrude=.0008
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    obj.location=loc;obj.rotation_euler=rotation;data.materials.append(mat)
    return obj
box('Exhibition plinth',(0,0,-.34),(L+.8,W+.8,.32),dark,.10)
box('Plinth reveal',(0,-W/2-.39,-.26),(L,.016,.027),screen)
lettering('PŘÍHODA   /   FABRIC AIR DISTRIBUTION',(-L*.43,-W/2-.407,-.39),min(.19,L/100),ivory)
for i in range(bays+1):
    x=-L/2+L*i/bays
    for y in (-W/2,W/2):
        for offset in (-.12,.12): box('Column flange',(x+offset,y,H/2),(.035,.32,H),steel)
        for xx in (-.16,.16):
            for yy in (-.17,.17): cylinder('Anchor bolt',(x+xx,y+yy,.16),(x+xx,y+yy,.21),.027,alloy,6)
    if i%2==0:
        box('Truss upper chord',(x,0,H+.13),(.1,W,.1),steel)
        steps=max(4,round(W/1.8))
        for k in range(steps):
            a=-W/2+W*k/steps;b=-W/2+W*(k+1)/steps
            cylinder('Roof truss diagonal',(x,a,H-.2),(x,b,H+.13),.027,steel,6)
    if i<bays:
        mid=x+L/bays/2
        box('Clerestory frame',(mid,W/2-.055,H*.84),(L/bays-.28,.07,.05),alloy)
        box('Back wall skirting',(mid,W/2-.11,.16),(L/bays,.1,.25),dark)
        for k in range(1,4):
            box('Window mullion',(x+L/bays*k/4,W/2-.065,H*.65),(.045,.06,H*.39),alloy)
        lettering('BAY '+str(i+1).zfill(2),(x+.4,W/2-.11,1.03),.20,ivory)
        for y in (-W*.2,W*.2):
            box('Light suspension',(mid,y,H-.28),(2.65,.12,.07),dark,.02)
            box('Linear LED',(mid,y,H-.32),(2.5,.07,.024),led)
if r['type']=='production_hall':
    for side in (-1,1):
        y=side*W*.33
        for idx,x in enumerate((-L*.28,0,L*.28)):
            box('Machine door gasket',(x-.2,y-.647,1.53),(.94,.018,.51),rubber,.015)
            box('Machine glazed inspection',(x-.2,y-.661,1.53),(.85,.014,.42),glass,.01)
            box('Machine handle',(x+.36,y-.70,1.4),(.04,.06,.25),alloy,.01)
            box('CNC display',(x+.72,y-.877,1.28),(.17,.012,.145),screen)
            for k in range(3): box('Display line',(x+.69,y-.886,1.31-k*.038),(.08,.003,.007),ivory)
            for k in range(5): box('Machine ventilation slot',(x+.62,y-.759,.52+k*.064),(.33,.015,.018),rubber)
            cylinder('Emergency stop',(x+.72,y-.872,1.10),(x+.72,y-.90,1.10),.035,red,12)
            lettering('CNC / '+str(idx+1).zfill(2),(x-.7,y-.763,.80),.10,dark)
            for xx in (-.8,.8):
                for yy in (-.6,.6): cylinder('Levelling foot',(x+xx,y+yy,.03),(x+xx,y+yy,.16),.09,rubber,12)
        for k in range(max(2,round(L/2))):
            box('Walkway edge',( -L/2+1+k*(L-2)/max(1,round(L/2)-1),side*W*.13,.015),(.55,.038,.012),ivory)
if r['type']!='sports_hall':
    for side in (-1,1):
        for z in (.18,1.3,2.4):
            for k in range(6): box('Timber pallet slat',(-L*.43,side*W*.29-.85+k*.34,z+.08),(.97,.18,.07),wood)
    lettering(('LOGISTICS' if r['type']=='warehouse' else 'PRODUCTION')+'  /  01',(-L*.35,-W*.10,.019),min(.38,W/35),ivory,rotation=(0,0,0))
    lettering('PEDESTRIAN ROUTE',(-L*.04,-W*.10,.019),min(.22,W/50),ivory,rotation=(0,0,0))

if r['type']=='warehouse':
    carton=material('Corrugated cardboard',rgb('#b39368'))
    for x in (-L*.28,0,L*.28):
        for y in (-W*.31,W*.31):
            shelf_height=min(H*.52,3.8)
            for xx in (-1.6,1.6):
                for yy in (-.55,.55): box('Warehouse rack upright',(x+xx,y+yy,shelf_height/2),(.10,.10,shelf_height),steel)
            for level in range(3):
                z=.15+level*(shelf_height-.4)/3
                box('Warehouse beam',(x,y-.57,z),(3.35,.10,.14),yellow)
                box('Warehouse beam',(x,y+.57,z),(3.35,.10,.14),yellow)
                box('Warehouse shelf',(x,y,z),(3.3,1.15,.07),alloy)
                for k in range(4):
                    box('Carton',(x-1.1+k*.73,y,z+.35),(.62,.87,.60),carton,.025)
                    box('Carton strap',(x-1.1+k*.73,y-.44,z+.35),(.035,.007,.56),ivory)
                    box('Shipping label',(x-1.22+k*.73,y-.445,z+.39),(.13,.008,.16),ivory)
if r['type']=='sports_hall':
    court=material('Sports court | maple',rgb('#b5976b'),.55)
    line=material('Court line',rgb('#f0eece'),.9)
    box('Maple sports floor',(0,0,.01),(L-.2,W-.2,.035),court)
    cl=min(L-2,28);cw=min(W-2,15)
    path('Court boundary',[(-cl/2,-cw/2,.036),(cl/2,-cw/2,.036),(cl/2,cw/2,.036),(-cl/2,cw/2,.036),(-cl/2,-cw/2,.036)],line,.025)
    path('Centre line',[(0,-cw/2,.038),(0,cw/2,.038)],line,.025)
    path('Centre circle',[(min(1.8,cw*.14)*math.cos(k*math.pi/32),min(1.8,cw*.14)*math.sin(k*math.pi/32),.038) for k in range(65)],line,.025)
    for side in (-1,1):
        x=side*(cl/2-.8)
        box('Basketball post',(side*(cl/2+.25),0,1.55),(.13,.16,3.1),steel)
        box('Backboard',(x,0,3.25),(.07,1.4,.9),ivory)
        path('Basketball hoop',[(x-side*.31+.24*math.cos(k*math.pi/16),.24*math.sin(k*math.pi/16),3.02) for k in range(33)],red,.025)
        path('Key markings',[(side*cl/2,-1.8,.038),(side*(cl/2-4.5),-1.8,.038),(side*(cl/2-4.5),1.8,.038),(side*cl/2,1.8,.038)],line,.025)
    lettering('PŘÍHODA   /   INDOOR AIR',(-L*.25,-W*.38,.04),min(.35,L/70),line,rotation=(0,0,0))

ducts=[]
trajectories=[]
nozzles=[]
rad=d['diameter_mm']/2000
length=d['length_m']
height=d['installation_height_m']
angle=0 if dist['direction']=='horizontal' else 90 if dist['direction']=='downward' else dist['angle_deg']
for i in range(d['count']):
    y=(i-(d['count']-1)/2)*d['spacing_m']
    if d['shape']=='circular':
        o=cylinder(f'Duct_{i+1:02d}',(-length/2,y,height),(length/2,y,height),rad,fabric,64)
    else:
        verts=[]
        for x in (-length/2,length/2):
            for j in range(33):
                a=math.pi+math.pi*j/32
                verts.append((x,rad*math.cos(a),rad*math.sin(a)))
        faces=[(j,j+1,j+34,j+33) for j in range(32)]+[(0,33,65,32),tuple(range(32,-1,-1)),tuple(range(33,66))]
        mesh=bpy.data.meshes.new('Semicircular fabric')
        mesh.from_pydata(verts,[],faces)
        mesh.materials.append(fabric)
        o=bpy.data.objects.new(f'Duct_{i+1:02d}',mesh)
        o.location=(0,y,height)
        bpy.context.collection.objects.link(o)
        for face in mesh.polygons: face.use_smooth=len(face.vertices)==4
    o['kind']='fabric_duct'
    if d['shape']=='semicircular':
        uv=o.data.uv_layers.new(name='Textile weave UV')
        for poly in o.data.polygons:
            for loop in poly.loop_indices:
                co=o.data.vertices[o.data.loops[loop].vertex_index].co
                uv.data[loop].uv=(co.x/.16,math.atan2(co.z,co.y)*rad/.16)
    o['color_hex']=d['color']
    o['installation_height_m']=height
    ducts.append(o)
    for j in range(max(2,round(length/2.8))+1):
        x=-length/2+length*j/max(2,round(length/2.8))
        cylinder('Suspension', (x,y,height+rad if d['shape']=='circular' else height),(x,y,H-.1),.012,wire,6)
        box('Suspension clamp',(x,y,H-.12),(.16,.10,.08),alloy,.012)
        start=0 if d['shape']=='circular' else math.pi
        sweep=2*math.pi if d['shape']=='circular' else math.pi
        pts=[(x,y+rad*1.008*math.cos(start+sweep*k/48),height+rad*1.008*math.sin(start+sweep*k/48)) for k in range(49)]
        path('Fabric seam',pts,seam,.008)
    total=max(4,min(22,round(length/1.6)))
    if dist['type']=='microperforation': total=min(55,round(length/.45))
    for j in range(total):
        x=-length/2+.6+(length-1.2)*j/max(1,total-1)
        sides=(1,) if angle==90 else (-1,1)
        for side in sides:
            vec=Vector((0,side*math.cos(math.radians(angle)),-math.sin(math.radians(angle))))
            origin=Vector((x,y,height))+vec*rad
            nozzle_len={'large_nozzles':.20,'small_nozzles':.095,'perforation':.013,'microperforation':.008}[dist['type']]
            nr={'large_nozzles':.070,'small_nozzles':.034,'perforation':.022,'microperforation':.009}[dist['type']]
            end=origin+vec*nozzle_len
            cylinder('Distribution nozzle',origin,end,nr,fabric if nozzle_len>.02 else seam,12)
            cylinder('Nozzle opening',end,end+vec*.006,nr*.83,dark,12)
            nozzles.append({'origin':list(end),'direction':list(vec),'angle_deg':angle})
            if dist['type']=='microperforation' and j%4: continue
            # Illustrative curved paths: no computed velocities or CFD fields.
            reach=min(3.3,W*.24)
            pts=[]
            for k in range(25):
                t=k/24
                px=x+.25*math.sin(math.pi*t)*side
                py=end.y+vec.y*reach*t
                pz=max(.2,end.z+vec.z*reach*t-(0 if angle==0 else 1.8)*t*t)
                py=max(-W/2+.2,min(W/2-.2,py))
                pts.append((px,py,pz))
            trajectories.append(pts)
            o=path('Airflow_line',pts,airmat,.012)
            o.hide_render=project['visualization']['airflow_mode']=='off'
            o.hide_viewport=o.hide_render
box('Occupied_zone',(0,0,.9),(L-.7,W-.7,1.8),zone)
for z in (.025,1.8):
    pts=[(-L/2+.35,-W/2+.35,z),(L/2-.35,-W/2+.35,z),(L/2-.35,W/2-.35,z),(-L/2+.35,W/2-.35,z),(-L/2+.35,-W/2+.35,z)]
    path('Occupied_zone_edge',pts,zoneedge,.009)
for o in bpy.data.objects:
    if o.name.startswith('Occupied_zone'):
        o.hide_render=not project['visualization']['show_occupied_zone']
        o.hide_viewport=o.hide_render
# World and broad soft lighting. Interactive use exports immediately; renders are explicit.
scene=bpy.context.scene
engine=os.environ.get('BLENDER_RENDER_ENGINE','BLENDER_EEVEE_NEXT')
if engine not in ('CYCLES','BLENDER_EEVEE_NEXT'):
    raise ValueError('BLENDER_RENDER_ENGINE must be CYCLES or BLENDER_EEVEE_NEXT')
scene.render.engine=engine
scene.cycles.device='CPU'
scene.cycles.samples=32
scene.cycles.use_denoising=True
scene.render.resolution_x=1600
scene.render.resolution_y=1000
scene.render.resolution_percentage=100
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.055,.08,.11,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.45
for loc,power,size in [((0,-5,H+9),11000,12),((-L*.3,5,H+7),14000,10),((L*.5,0,H+4),7000,8)]:
    bpy.ops.object.light_add(type='AREA',location=loc)
    bpy.context.object.data.energy=power
    bpy.context.object.data.shape='DISK'
    bpy.context.object.data.size=size
    bpy.context.object.rotation_euler=(Vector((0,0,H*.3))-bpy.context.object.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(L*.82,-W*1.75,H*2.15))
camera=bpy.context.object
camera.rotation_euler=(Vector((0,0,H*.38))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO'
camera.data.ortho_scale=max(L*1.3,W*2)
scene.camera=camera
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
scene.view_settings.exposure=-1.2
scene.view_settings.look='AgX - Medium High Contrast'
scene.render.film_transparent=False
status('Preparing 3D model')
bpy.context.view_layer.update()
manifest={'project':project,'ducts':[{'name':o.name,'location':list(o.location),'dimensions':list(o.dimensions),'color':d['color']} for o in ducts],
    'nozzles':nozzles,'trajectories':trajectories,'coordinate_system':'blender_z_up','disclaimer':'Illustrative airflow — not CFD.'}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
# Batch static architecture by material to keep the live viewer smooth on an
# integrated GPU. Ducts, outlets and visibility groups remain individually named.
import bmesh
depsgraph=bpy.context.evaluated_depsgraph_get()
groups={}
for obj in list(bpy.data.objects):
    if obj.type not in ('MESH','FONT','CURVE') or obj.name.startswith(('Duct_','Distribution nozzle','Nozzle opening','Airflow_line','Occupied_zone')):
        continue
    if not obj.data.materials: continue
    groups.setdefault(obj.data.materials[0].name,[]).append(obj)
for matname,objects in groups.items():
    bm=bmesh.new()
    for obj in objects:
        mesh=bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
        mesh.transform(obj.matrix_world)
        bm.from_mesh(mesh)
        bpy.data.meshes.remove(mesh)
    mesh=bpy.data.meshes.new('Architecture / '+matname);bm.to_mesh(mesh);bm.free()
    mesh.materials.append(bpy.data.materials[matname])
    obj=bpy.data.objects.new('Architecture / '+matname,mesh);bpy.context.collection.objects.link(obj)
    for original in objects: bpy.data.objects.remove(original,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'))
# Keep paths in the .blend / PNG; the viewer uses identical manifest paths for animation.
for o in bpy.data.objects:
    o.select_set(not o.name.startswith('Airflow_line') and o.type not in ('LIGHT','CAMERA'))
bpy.ops.export_scene.gltf(filepath=str(out/'model.glb'),export_format='GLB',use_selection=True,export_cameras=False,export_lights=False,export_extras=True)
if options.render:
    status('Rendering preview')
    scene.render.filepath=str(out/'preview.png')
    bpy.ops.render.render(write_still=True)
status('Ready')
