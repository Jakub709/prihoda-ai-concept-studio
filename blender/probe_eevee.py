import bpy, time
from pathlib import Path
start=time.monotonic()
bpy.ops.wm.open_mainfile(filepath=str(Path(__file__).resolve().parents[1]/'output/final-render/scene.blend'))
scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE_NEXT'
scene.render.resolution_x=960
scene.render.resolution_y=600
scene.render.filepath=str(Path(__file__).resolve().parents[1]/'output/eevee-probe.png')
scene.render.film_transparent=False
bpy.ops.render.render(write_still=True)
print('EEVEE_SECONDS',round(time.monotonic()-start,2),flush=True)
