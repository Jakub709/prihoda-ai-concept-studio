import { forwardRef, useEffect, useImperativeHandle, useLayoutEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import type { ModelResult, Project } from './model'

export type ViewerHandle={camera:(preset:string)=>void;zoom:(factor:number)=>void;exportPNG:()=>Promise<Blob>}
function disposeTree(root:THREE.Object3D){
 const materials=new Set<THREE.Material>(),textures=new Set<THREE.Texture>()
 root.traverse(o=>{
  if(o instanceof THREE.Mesh||o instanceof THREE.Line||o instanceof THREE.Points){o.geometry.dispose();(Array.isArray(o.material)?o.material:[o.material]).forEach(m=>materials.add(m))}
  else if(o instanceof THREE.Sprite)materials.add(o.material)
 })
 for(const material of materials){for(const value of Object.values(material))if(value instanceof THREE.Texture)textures.add(value);material.dispose()}
 textures.forEach(texture=>texture.dispose())
}
type Props={model:ModelResult;project:Project;airflow:string;occupied:boolean;dimensions:boolean;tour?:boolean;onReady:()=>void;onUnavailable:()=>void}
export const Viewer=forwardRef<ViewerHandle,Props>(function Viewer({model,project,airflow,occupied,dimensions,tour=false,onReady,onUnavailable},ref){
 const {length_m:L,width_m:W,height_m:H}=project.room
 const host=useRef<HTMLDivElement>(null)
 const engine=useRef<{renderer:THREE.WebGLRenderer;camera:THREE.PerspectiveCamera;controls:OrbitControls;scene:THREE.Scene;fit:(p:string)=>void}|null>(null)
 const display=useRef({airflow,occupied,dimensions,tour})
 const readyCallback=useRef(onReady),unavailableCallback=useRef(onUnavailable)
 useLayoutEffect(()=>{display.current={airflow,occupied,dimensions,tour};readyCallback.current=onReady;unavailableCallback.current=onUnavailable},[airflow,occupied,dimensions,tour,onReady,onUnavailable])
 const [error,setError]=useState('')
 const [loading,setLoading]=useState(true)
 useImperativeHandle(ref,()=>({
  camera(p){engine.current?.fit(p)},
  zoom(f){const e=engine.current;if(e){e.camera.position.sub(e.controls.target).multiplyScalar(f).add(e.controls.target);e.controls.update()}},
  exportPNG(){
   return new Promise<Blob>((resolve,reject)=>{
    const e=engine.current;if(!e){reject(new Error('The 3D view is not ready.'));return}
    e.renderer.render(e.scene,e.camera)
    e.renderer.domElement.toBlob(blob=>blob?resolve(blob):reject(new Error('The image could not be captured.')),'image/png')
   })
  }
 }))
 useEffect(()=>{
  if(!host.current)return
  const container=host.current
  let cancelled=false,frame=0,modelRoot:THREE.Object3D|undefined
  setError('');setLoading(true)
  delete container.dataset.model;delete container.dataset.ductCount
  unavailableCallback.current()
  let renderer:THREE.WebGLRenderer
  try{renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true,alpha:false})}
  catch{setError('Interactive 3D is unavailable on this device.');setLoading(false);return}
  renderer.setPixelRatio(Math.min(window.devicePixelRatio,1.5))
  renderer.setClearColor('#101c26')
  renderer.shadowMap.enabled=true
  renderer.shadowMap.type=THREE.PCFShadowMap
  renderer.toneMapping=THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure=1.0
  renderer.domElement.setAttribute('aria-label','Interactive 3D fabric duct concept. Drag to orbit, scroll to zoom, right-drag to pan.')
  renderer.domElement.setAttribute('tabindex','0')
  container.appendChild(renderer.domElement)
  const scene=new THREE.Scene()
  const camera=new THREE.PerspectiveCamera(36,1,.1,600)
  const controls=new OrbitControls(camera,renderer.domElement)
  controls.enableDamping=true
  controls.dampingFactor=.10
  controls.maxPolarAngle=Math.PI*.49
  controls.minDistance=2
  controls.maxDistance=300
  const env=new RoomEnvironment()
  const pmrem=new THREE.PMREMGenerator(renderer)
  const envTarget=pmrem.fromScene(env)
  scene.environment=envTarget.texture
  scene.environmentIntensity=.55
  scene.add(new THREE.HemisphereLight(0xcfe8ff,0x243743,.85))
  const sun=new THREE.DirectionalLight(0xfff4df,2.3)
  sun.position.set(-L*.3,H+12,W*.7)
  sun.castShadow=true
  sun.shadow.mapSize.set(2048,2048)
  Object.assign(sun.shadow.camera,{left:-L,right:L,top:L,bottom:-L,near:.1,far:150})
  sun.shadow.bias=-.0005
  sun.shadow.normalBias=.03
  scene.add(sun)
  const fill=new THREE.DirectionalLight(0xc7e4fa,1.4)
  fill.position.set(L,H,-W);scene.add(fill)
  const front=new THREE.DirectionalLight(0xffffff,.75);front.position.set(0,H,W*2);scene.add(front)
  const grid=new THREE.GridHelper(Math.max(L,W)*5,100,0x334d60,0x253b4b)
  grid.position.y=-.53
  ;(grid.material as THREE.Material).transparent=true;(grid.material as THREE.Material).opacity=.20
  scene.add(grid)
  const ground=new THREE.Mesh(new THREE.PlaneGeometry(400,400),new THREE.MeshBasicMaterial({color:0x101c26,toneMapped:false}))
  ground.rotation.x=-Math.PI/2;ground.position.y=-.55;ground.receiveShadow=true;scene.add(ground)
  const contact=new THREE.Mesh(new THREE.PlaneGeometry(400,400),new THREE.ShadowMaterial({opacity:.28}))
  contact.rotation.x=-Math.PI/2;contact.position.y=-.545;contact.receiveShadow=true;scene.add(contact)
  const target=new THREE.Vector3(0,H*.42,0)
  let transition:{from:THREE.Vector3;to:THREE.Vector3;fromTarget:THREE.Vector3;toTarget:THREE.Vector3;start:number}|null=null
  let initialized=false
  function fit(preset:string){
   const from=camera.position.clone(),fromTarget=controls.target.clone()
   controls.target.copy(target)
   const extent=Math.max(L,W)
   const dirs:Record<string,THREE.Vector3>={Overview:new THREE.Vector3(.96,.62,1.3),Front:new THREE.Vector3(.001,.26,1),Side:new THREE.Vector3(1,.23,.001),Inside:new THREE.Vector3(1,.12,.17)}
   let dir=dirs[preset]||dirs.Overview
   if(preset==='Detail'){
    const y=-(project.ducts.count-1)*project.ducts.spacing_m/2
    controls.target.set(-project.ducts.length_m*.25,project.ducts.installation_height_m,-y)
    camera.position.set(-project.ducts.length_m*.25+3,project.ducts.installation_height_m-1.1,-y+3)
   }else if(preset==='Inside'){
    controls.target.set(-L*.3,Math.min(H*.62,3.7),0)
    camera.position.set(L*.42,Math.min(H*.52,3.2),W*.05)
   }else{
    dir=dir.clone().normalize()
    camera.position.copy(target).addScaledVector(dir,extent*2)
    camera.lookAt(target)
    camera.updateMatrixWorld()
    const corners=[]
    for(const x of [-L/2,L/2])for(const y of [0,H])for(const z of [-W/2,W/2])corners.push(new THREE.Vector3(x,y,z))
    let distance=extent*3
    // Fit the actual room bounds at the chosen view angle.
    for(let n=0;n<90;n++){
      camera.position.copy(target).addScaledVector(dir,distance);camera.updateMatrixWorld()
      const max=Math.max(...corners.flatMap(v=>{const p=v.clone().project(camera);return [Math.abs(p.x),Math.abs(p.y)]}))
      if(max>=.90)break
      distance*=.975
    }
   }
   controls.update()
   if(initialized){transition={from,to:camera.position.clone(),fromTarget,toTarget:controls.target.clone(),start:performance.now()};camera.position.copy(from);controls.target.copy(fromTarget)}
   initialized=true
  }
  controls.addEventListener('start',()=>{transition=null})
  engine.current={renderer,camera,controls,scene,fit}
  const observer=new ResizeObserver(()=>{
   if(!container.clientWidth||!container.clientHeight)return
   renderer.setSize(container.clientWidth,container.clientHeight)
   camera.aspect=container.clientWidth/container.clientHeight;camera.updateProjectionMatrix()
   fit('Overview')
  })
  observer.observe(container)
  renderer.setSize(container.clientWidth,container.clientHeight)
  camera.aspect=container.clientWidth/container.clientHeight;camera.updateProjectionMatrix();fit('Overview')

  const airGroup=new THREE.Group()
  const dimensionGroup=new THREE.Group()
  scene.add(airGroup,dimensionGroup)
  let curves:THREE.CatmullRomCurve3[]=[]
  let particles:THREE.Points|undefined
  const particleCountPerPath=3
  const occupiedMeshes:THREE.Object3D[]=[]
  function dimText(text:string,position:THREE.Vector3){
   const c=document.createElement('canvas');c.width=384;c.height=96
   const ctx=c.getContext('2d')!
   ctx.clearRect(0,0,384,96)
   ctx.fillStyle='#b7ccda';ctx.font='500 44px Arial';ctx.textAlign='center';ctx.fillText(text,192,60)
   const texture=new THREE.CanvasTexture(c)
   const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:texture,depthTest:false}))
   sprite.scale.set(4.2,1.05,1);sprite.position.copy(position);dimensionGroup.add(sprite)
  }
  function dimension(a:THREE.Vector3,b:THREE.Vector3,label:string,offset:THREE.Vector3){
   dimensionGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([a,b]),new THREE.LineBasicMaterial({color:0x8798a6})))
   for(const v of [a,b]){
    const line=[v.clone().add(new THREE.Vector3(0,.18,0)),v.clone().add(new THREE.Vector3(0,-.18,0))]
    dimensionGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(line),new THREE.LineBasicMaterial({color:0x8798a6})))
   }
   dimText(label,a.clone().lerp(b,.5).add(offset))
  }
  dimension(new THREE.Vector3(-L/2,.03,W/2+1.4),new THREE.Vector3(L/2,.03,W/2+1.4),L+' m',new THREE.Vector3(0,0,.55))
  dimension(new THREE.Vector3(L/2+1.3,.03,-W/2),new THREE.Vector3(L/2+1.3,.03,W/2),W+' m',new THREE.Vector3(.7,0,0))

  // Each view owns its requests, including when Undo revisits the same GLB.
  const download=new AbortController()
  const downloadTimeout=window.setTimeout(()=>download.abort(),45000)
  const viewRequest=crypto.randomUUID()
  async function loadModel(){
   const responses=await Promise.all([model.model_url,model.manifest_url].map(path=>{
    const url=new URL(path,window.location.href)
    // Do not alter signed cloud URLs. Local assets get an independent request URL.
    if(url.origin===window.location.origin)url.searchParams.set('view',viewRequest)
    return fetch(url,{signal:download.signal,cache:'no-store'})
   }))
   for(const response of responses){
    if(response.status===401)window.dispatchEvent(new Event('studio-session-expired'))
    if(!response.ok)throw new Error('The model download failed.')
   }
   const [bytes,manifest]=await Promise.all([responses[0].arrayBuffer(),responses[1].json()])
   if(download.signal.aborted)throw new Error('The model download was cancelled.')
   const gltf=await new GLTFLoader().parseAsync(bytes,new URL('.',new URL(model.model_url,window.location.href)).href)
   return {gltf,manifest}
  }
  loadModel().then(({gltf,manifest})=>{
   if(cancelled){disposeTree(gltf.scene);return}
   modelRoot=gltf.scene
   modelRoot.traverse(o=>{
    if(o instanceof THREE.Mesh){
     o.castShadow=true;o.receiveShadow=true
     if(o.name.startsWith('Occupied_zone')){
      occupiedMeshes.push(o);o.castShadow=false;o.receiveShadow=false
      const mats=Array.isArray(o.material)?o.material:[o.material]
      for(const m of mats){m.transparent=true;m.depthWrite=false}
     }
     if(o.name.startsWith('Duct_')){
      o.userData.isFabricDuct=true
      const mats=Array.isArray(o.material)?o.material:[o.material]
      for(const m of mats)if(m instanceof THREE.MeshStandardMaterial){
       m.roughness=.96;m.metalness=0
       if(m instanceof THREE.MeshPhysicalMaterial){m.sheen=.18;m.sheenColor.copy(m.color);m.sheenRoughness=1}
      }
     }
    }
   })
   scene.add(modelRoot)
   curves=(manifest.trajectories||[]).map((pts:number[][])=>new THREE.CatmullRomCurve3(pts.map(v=>new THREE.Vector3(v[0],v[2],-v[1]))))
   curves.forEach(curve=>{
    const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(curve.getPoints(45)),new THREE.LineBasicMaterial({color:0x72ddf5,transparent:true,opacity:.22}))
    airGroup.add(line)
   })
   const positions=new Float32Array(curves.length*particleCountPerPath*3)
   const geometry=new THREE.BufferGeometry()
   geometry.setAttribute('position',new THREE.BufferAttribute(positions,3))
   particles=new THREE.Points(geometry,new THREE.PointsMaterial({color:0xa1efff,size:.065,transparent:true,opacity:.88,depthWrite:false}))
   airGroup.add(particles)
   setLoading(false)
   container.dataset.model=model.id
   container.dataset.ductCount=String(manifest.ducts?.length||0)
   readyCallback.current()
  }).catch(()=>{if(!cancelled){setError('The 3D model could not be loaded. Reopen the saved project or generate the concept again.');setLoading(false);unavailableCallback.current()}}).finally(()=>window.clearTimeout(downloadTimeout))
  let previous=0,tourStart=0,wasTour=false
  function animate(time:number){
   frame=requestAnimationFrame(animate)
   if(time-previous<30)return
   previous=time
   controls.update()
   const mode=display.current
   if(transition){
    const t=Math.min(1,(time-transition.start)/1200),ease=t*t*(3-2*t)
    camera.position.lerpVectors(transition.from,transition.to,ease)
    controls.target.lerpVectors(transition.fromTarget,transition.toTarget,ease)
    controls.update();if(t===1)transition=null
   }
   if(mode.tour){
    if(!wasTour){tourStart=time;transition=null}
    const t=(time-tourStart)/1000,angle=.62+Math.sin(t*.09)*.38
    const distance=Math.max(L,W)*Math.max(1.2,1.65/camera.aspect)
    const desired=new THREE.Vector3(Math.sin(angle)*distance,H*.42+distance*.4+Math.sin(t*.15)*H*.13,Math.cos(angle)*distance)
    camera.position.lerp(desired,.018);controls.target.lerp(target,.025);controls.update()
   }
   wasTour=mode.tour
   airGroup.visible=mode.airflow!=='off'
   dimensionGroup.visible=mode.dimensions
   occupiedMeshes.forEach(o=>o.visible=mode.occupied)
   if(particles){
    particles.visible=mode.airflow==='animated'
    const a=particles.geometry.attributes.position as THREE.BufferAttribute
    if(particles.visible)curves.forEach((curve,i)=>{
     for(let j=0;j<particleCountPerPath;j++){
      const t=(time*.00014+j/particleCountPerPath+(i%7)/11)%1
      const point=curve.getPoint(t);a.setXYZ(i*particleCountPerPath+j,point.x,point.y,point.z)
     }
    })
    a.needsUpdate=true
   }
   renderer.render(scene,camera)
  }
  frame=requestAnimationFrame(animate)
  const lost=(e:Event)=>{e.preventDefault();setError('The 3D session was interrupted. Reload the page to restore the viewer.');unavailableCallback.current()}
  renderer.domElement.addEventListener('webglcontextlost',lost)
  return()=>{
   cancelled=true;download.abort();window.clearTimeout(downloadTimeout);cancelAnimationFrame(frame);observer.disconnect();controls.dispose()
   renderer.domElement.removeEventListener('webglcontextlost',lost)
   disposeTree(scene)
   envTarget.dispose();env.dispose();pmrem.dispose();renderer.dispose();renderer.domElement.remove();engine.current=null
  }
 },[model.model_url,model.manifest_url,model.id,L,W,H,project.ducts.count,project.ducts.spacing_m,project.ducts.length_m,project.ducts.installation_height_m])
 return <div className="viewer-host" ref={host}>
  {loading&&<div className="viewer-loading"><span className="spinner"/><span>Preparing 3D model</span></div>}
  {error&&<div className="viewer-fallback">{model.preview_url&&<img src={model.preview_url} alt="Blender render of this concept"/>}<p role="alert">{error}</p>{model.preview_url&&<small>Rendered preview · interactive controls unavailable</small>}</div>}
 </div>
})
