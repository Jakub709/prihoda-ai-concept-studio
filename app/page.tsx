import { useEffect, useRef, useState } from 'react'
import { ArrowRight, ArrowUp, Box, Check, ChevronDown, ChevronRight, CircleHelp, Code2, Download, Factory, FileText, Focus, Layers3, LoaderCircle, Maximize2, MoveUpRight, Plus, Settings2, SlidersHorizontal, Sparkles, Undo2, Wind, X, ZoomIn, ZoomOut, AlertCircle, CircleCheck } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '@/components/ui/collapsible'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Viewer, type ViewerHandle } from './viewer'
import { Connections, ProjectLibrary } from './cloud'
import { DEMO, DEMO_MODEL, api, valueAt, setAt, labels, formatted, type Project, type ModelResult, type Change, type ProjectValue, type Receipt, type BackendStatus, type ParsedProject, type ModifiedProject, type GenerationJob, type SavedProject } from './model'

const example='We have a production hall 30 × 15 × 6 m. Required airflow is 7,000 m³/h. We are considering two circular fabric ducts, diameter 600 mm, 22 m long, installed 4.5 m above the floor. Supply temperature 16 °C, room temperature 22 °C. Use large nozzles angled 30° downward.'
const suggestions=['Use three red ducts','Move the ducts 1 m higher','Increase diameter to 800 mm','Point the nozzles 35° downward']
const colors=['#eeeeee','#d71920','#2874ad','#475c50','#50565d','#25282c']
const clone=<T,>(x:T):T=>structuredClone(x)

function Tip({text,children}:{text:string;children:React.ReactElement}){
 return <Tooltip><TooltipTrigger render={children}/><TooltipContent>{text}</TooltipContent></Tooltip>
}
function Section({title,icon:Icon,children,defaultOpen=true}:{title:string;icon:LucideIcon;children:React.ReactNode;defaultOpen?:boolean}){
 return <Collapsible className="parameter-section" defaultOpen={defaultOpen}>
 <CollapsibleTrigger className="section-heading"><Icon size={16}/><span>{title}</span><ChevronDown size={15}/></CollapsibleTrigger>
 <CollapsibleContent className="section-content">{children}</CollapsibleContent>
 </Collapsible>
}
function Picker({value,options,onChange,label}:{value:string;options:[string,string][];onChange:(s:string)=>void;label:string}){
 return <Select value={value} onValueChange={v=>v&&onChange(v)}><SelectTrigger className="field-select" aria-label={label}><SelectValue>{options.find(o=>o[0]===value)?.[1]||value}</SelectValue></SelectTrigger><SelectContent>{options.map(([v,t])=><SelectItem key={v} value={v}>{t}</SelectItem>)}</SelectContent></Select>
}

export default function App({allowSettings=true}:{allowSettings?:boolean}){
 const [status,setStatus]=useState<{blender_ready:boolean;ai_mode:string;blender_name?:string}|null|undefined>(undefined)
 const [active,setActive]=useState(false)
 const [request,setRequest]=useState('')
 const [draft,setDraft]=useState<Project>(clone(DEMO))
 const [shown,setShown]=useState<Project>(clone(DEMO))
 const [model,setModel]=useState<ModelResult>(DEMO_MODEL)
 const [command,setCommand]=useState('')
 const [busy,setBusy]=useState(false)
 const [stage,setStage]=useState('')
 const [error,setError]=useState('')
 const [notice,setNotice]=useState('')
 const [generated,setGenerated]=useState(false)
 const [changes,setChanges]=useState<Change[]>([])
 const [previous,setPrevious]=useState<{project:Project;extracted:string[];unconfirmed:string[]}|null>(null)
 const [extracted,setExtracted]=useState<string[]>([])
 const [unconfirmed,setUnconfirmed]=useState<string[]>([])
 const [airflow,setAirflow]=useState<'off'|'lines'|'animated'>('animated')
 const [occupied,setOccupied]=useState(false)
 const [dimensions,setDimensions]=useState(true)
 const [camera,setCamera]=useState('Overview')
 const [settings,setSettings]=useState(false)
 const [identity,setIdentity]=useState<{project_id:string;version:number;latest_version?:number}|null>(null)
 const [receipt,setReceipt]=useState<Receipt|null>(null)
 const [presenting,setPresenting]=useState(false)
 const [tour,setTour]=useState(false)
 const [jsonOpen,setJsonOpen]=useState(false)
 const [requestOpen,setRequestOpen]=useState(false)
 const [exporting,setExporting]=useState(false)
 const [pngExport,setPngExport]=useState<{url:string;filename:string}|null>(null)
 const [readyModel,setReadyModel]=useState<string|null>(null)
 const viewerReady=readyModel===model.model_url
 const [generationCount,setGenerationCount]=useState(0)
 const viewer=useRef<ViewerHandle>(null)
 const commandInput=useRef<HTMLInputElement>(null)
 const viewport=useRef<HTMLDivElement>(null)
 const mounted=useRef(true)
 useEffect(()=>{
  mounted.current=true
  const read=()=>api<BackendStatus>('/status').then(setStatus).catch(()=>setStatus(null))
  void read();const timer=setInterval(()=>void read(),15000)
  return()=>{mounted.current=false;clearInterval(timer)}
 },[])
 useEffect(()=>{if(!notice)return;const timer=setTimeout(()=>setNotice(''),6500);return()=>clearTimeout(timer)},[notice])
 const dirty=JSON.stringify(draft)!==JSON.stringify(shown)
 const missing=Object.values(draft.air).filter(v=>v===null).length
 const mode=status?.ai_mode==='openai'?'AI MODE':'DEMO MODE'
 function update(path:string,value:ProjectValue){
  if(busy)return
  setDraft(p=>setAt(p,path,value));setUnconfirmed(a=>a.filter(x=>x!==path));setExtracted(a=>a.filter(x=>x!==path));setNotice('')
 }
 function field(path:string,label:string,unit='',step=1){
  const rawValue=valueAt(draft,path)
  const value=typeof rawValue==='boolean'?Number(rawValue):rawValue
  const provenance=value===null?'Missing':unconfirmed.includes(path)?'Confirm':extracted.includes(path)?'Extracted':'Provided'
  return <label className="field" key={path}><span className="field-label">{label}<span className={'field-status '+provenance.toLowerCase()} title={provenance==='Confirm'?'Example value. Confirm before generating your concept.':provenance}>{provenance==='Provided'?<Check size={11}/>:provenance==='Extracted'?<Sparkles size={11}/>:<span>{provenance}</span>}</span></span><span className={'input-wrap '+(value===null?'missing-input':'')}><input aria-label={label} type="number" step={step} value={value??''} placeholder="Not provided" disabled={busy} onChange={e=>{const v=e.target.value;update(path,v===''?(path.startsWith('air.')?null:0):Number(v))}}/><span>{unit}</span></span></label>
 }
 function loadDemo(){
  if(busy)return
  setError('');setNotice('');setActive(true);setDraft(clone(DEMO));setShown(clone(DEMO));setModel(DEMO_MODEL)
  setExtracted([]);setUnconfirmed([]);setPrevious(null);setChanges([]);setGenerated(false);setCamera('Overview')
  setAirflow('animated');setOccupied(false);setDimensions(true)
  setTour(false);setCamera('Overview');viewer.current?.camera('Overview')
  setIdentity(null);setReceipt(null)
 }
 function newConcept(){
  if(busy)return
  setActive(false);setRequest('');setError('');setNotice('');setPrevious(null);setChanges([])
  setDraft(clone(DEMO));setShown(clone(DEMO));setModel(DEMO_MODEL);setGenerated(false)
  setCommand('');setExtracted([]);setUnconfirmed([]);setTour(false);setPresenting(false)
  setAirflow('animated');setOccupied(false);setDimensions(true);setCamera('Overview');viewer.current?.camera('Overview')
  setIdentity(null);setReceipt(null)
 }
 async function analyze(){
  if(request.trim().length<3){setError('Describe the hall and its requirements, or load the demo project.');return}
  setBusy(true);setStage('Understanding request');setError('')
  try{
   const data=await api<ParsedProject>('/parse',{text:request})
   setReceipt(data.receipt||{provider:data.provider})
   setDraft(data.project);setExtracted(data.extracted);setUnconfirmed(data.unconfirmed)
   setActive(true);setGenerated(false);setNotice(data.extracted.length+' parameters extracted. Review values marked “Confirm” before generating.')
   setChanges([]);setPrevious(null)
  }catch(e){setError((e as Error).message)}finally{setBusy(false);setStage('')}
 }
 async function generate(next:Project,render=false):Promise<ModelResult>{
  await api('/validate',next)
  setStage('Generating geometry')
  let job=await api<GenerationJob>('/generate'+(render?'?render=true':''),next)
  const deadline=Date.now()+(render?660000:165000)
  while(job.state!=='ready'){
   if(job.state==='error')throw new Error(job.error)
   if(Date.now()>deadline)throw new Error('Generation is taking longer than expected. Your previous concept is preserved. Try again.')
   setStage(job.stage)
   await new Promise(r=>setTimeout(r,400))
   if(!mounted.current)throw new Error('View closed')
   job=await api<GenerationJob>('/jobs/'+job.id)
  }
  setStage('Preparing 3D model')
  if(!job.model_url||!job.manifest_url)throw new Error('The generated model is incomplete. Try again.')
  return {...job,model_url:job.model_url,manifest_url:job.manifest_url}
 }
 async function build(){
  setBusy(true);setError('');setNotice('')
  try{
   const result=await generate(draft)
   setShown(clone(draft));setModel(result);setGenerated(true);setGenerationCount(n=>n+1)
   setPrevious(null);setChanges([]);setCamera('Overview')
   setNotice('Concept generated from validated project parameters.')
  }catch(e){setError((e as Error).message)}finally{setBusy(false);setStage('')}
 }
 async function modify(){
  if(!command.trim()||busy)return
  setBusy(true);setError('');setNotice('');setStage('Understanding request')
  try{
   // Always modify the displayed concept, never a hidden or stale draft.
   const data=await api<ModifiedProject>('/modify',{command,project:shown})
   setReceipt(data.receipt)
   setStage(data.changes.length+' changes detected')
   const result=await generate(data.project)
   setPrevious({project:clone(shown),extracted:[...extracted],unconfirmed:[...unconfirmed]})
   setShown(data.project);setDraft(clone(data.project));setModel(result);setGenerated(true);setGenerationCount(n=>n+1)
   setChanges(data.changes);setCommand('');setExtracted(data.changes.map((c:Change)=>c.path));setUnconfirmed(a=>a.filter(x=>!data.changes.some((c:Change)=>c.path===x)))
   setCamera('Overview')
  }catch(e){setError((e as Error).message)}finally{setBusy(false);setStage('')}
 }
 async function undo(){
  if(!previous||busy)return
  setBusy(true);setError('');setStage('Restoring previous concept')
  try{
   const result=await generate(previous.project)
   setShown(clone(previous.project));setDraft(clone(previous.project));setModel(result)
   setExtracted(previous.extracted);setUnconfirmed(previous.unconfirmed);setPrevious(null);setChanges([])
   setGenerated(true);setGenerationCount(n=>n+1);setNotice('Previous concept restored.');setCamera('Overview')
  }catch(e){setError((e as Error).message)}finally{setBusy(false);setStage('')}
 }
 function preset(p:string){setTour(false);setCamera(p);viewer.current?.camera(p)}
 function manual(){
  setActive(true);setDraft(clone(DEMO));setGenerated(false)
  setUnconfirmed(Object.keys(labels));setExtracted([]);setNotice('Example values are shown to help you start. Review and enter your project parameters.')
 }
 function usePreview(){loadDemo();setNotice('Demo preview loaded. This is a previously generated Blender model; new geometry requires the 3D engine.')}
 function downloadJSON(){const a=document.createElement('a');const u=URL.createObjectURL(new Blob([JSON.stringify(draft,null,2)],{type:'application/json'}));a.href=u;a.download='prihoda-project.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)}
 const canModify=active&&generated&&viewerReady&&!dirty&&!busy
 async function capturePreview(){
  if(!viewer.current)throw new Error('The 3D view is not ready.')
  const blob=await viewer.current.exportPNG()
  const response=await fetch('/api/export-preview',{method:'POST',headers:{'Content-Type':'image/png'},body:blob})
  if(response.status===401)window.dispatchEvent(new Event('studio-session-expired'))
  const data=await response.json()
  if(!response.ok)throw new Error(data.detail||'Preview capture failed.')
  return data.filename as string
 }
 async function renderStill(){
  setBusy(true);setError('');setNotice('')
  try{
   const result=await generate({...shown,visualization:{...shown.visualization,airflow_mode:airflow,show_occupied_zone:occupied,show_dimensions:dimensions}},true)
   if(!result.preview_url)throw new Error('The render was not created.')
   setPngExport({url:result.preview_url,filename:'prihoda-blender-render.png'})
  }catch(e){setError((e as Error).message)}finally{setBusy(false);setStage('')}
 }
 function loadSaved(data:SavedProject){
  setDraft(clone(data.project));setShown(clone(data.project));setModel(data.model);setIdentity(data)
  setActive(true);setGenerated(true);setChanges([]);setPrevious(null);setReceipt(null);setError('')
  setExtracted([]);setUnconfirmed([]);setAirflow(data.project.visualization.airflow_mode)
  setOccupied(data.project.visualization.show_occupied_zone);setDimensions(data.project.visualization.show_dimensions)
 }
 async function exportPNG(){
  if(!viewer.current)return
  setExporting(true);setError('')
  try{
   const blob=await viewer.current.exportPNG()
   const response=await fetch('/api/export-preview',{method:'POST',headers:{'Content-Type':'image/png'},body:blob})
   if(response.status===401)window.dispatchEvent(new Event('studio-session-expired'))
   const data=await response.json()
   if(!response.ok)throw new Error(data.detail||'The PNG could not be saved.')
   setPngExport(data)
  }catch(e){setError((e as Error).message)}finally{setExporting(false)}
 }
 return <TooltipProvider delay={250}><div className={'app-shell '+(presenting?'presentation-mode':'')}>
  <header className="topbar">
   <div className="brand-lockup"><a href="/" aria-label="PŘÍHODA – úvodní stránka"><img src="/brand/prihoda-logo.svg" alt="PŘÍHODA" className="brand-logo"/></a><span className="brand-divider"/><div className="app-name">AI Concept Studio<span className="experimental">STUDIO / 02</span></div></div>
   <div className="header-actions"><ProjectLibrary project={{...shown,visualization:{...shown.visualization,airflow_mode:airflow,show_occupied_zone:occupied,show_dimensions:dimensions}}} model={model} dirty={dirty} busy={busy} canSave={viewerReady} identity={identity} onIdentity={v=>{setIdentity(v);setDraft(p=>({...p,project_name:v.name||p.project_name}));setShown(p=>({...p,project_name:v.name||p.project_name}))}} onLoad={loadSaved} capture={capturePreview} onConnect={()=>allowSettings?setSettings(true):setNotice('Ask your studio administrator to connect the project library.')} onNotice={setNotice}/><button className="text-button" onClick={newConcept} disabled={busy}><Plus size={16}/>New concept</button><button className="outline-button demo-button" onClick={loadDemo} disabled={busy}><Box size={16}/>Demo project</button>{allowSettings&&<><span className="header-divider"/><Tip text="System settings"><button className="icon-button" aria-label="System settings" onClick={()=>setSettings(true)}><Settings2 size={19}/></button></Tip></>}</div>
  </header>
  <div className="projectbar"><div className="project-title"><span className="project-symbol"><Factory size={21}/></span><div><div className="overline">FABRIC AIR DISTRIBUTION</div><h1>{active?draft.project_name:'A new perspective on your next project'}</h1></div>{active&&<span className="draft-badge">{generated?'Concept':'Draft'}</span>}</div><nav aria-label="Concept progress" className="flow-steps"><button type="button" className={!active?'current':'complete'} onClick={()=>active?setRequestOpen(true):document.getElementById('customer-request')?.focus()} aria-label={active?'Původní zadání':'Zadat požadavek'}><b>{active?<Check size={12}/>:1}</b>Request</button><ChevronRight size={14}/><span className={active&&!generated?'current':generated?'complete':''}><b>{generated?<Check size={12}/>:2}</b>Parameters</span><ChevronRight size={14}/><span className={generated?'current':''}><b>3</b>3D concept</span></nav></div>
  <main className={'workspace '+(!active?'welcome-workspace':'')}>
   <aside className="sidebar">
    {!active?<div className="request-panel"><span className="section-kicker"><span/>START WITH A REQUEST</span><h2>From a customer’s words.<br/><em>To a clear concept.</em></h2><p className="intro">Describe the space and ventilation requirements. Turn them into a structured project and a fabric duct visualization.</p><label className="request-label" htmlFor="customer-request">Customer request<button className="inline-link" onClick={()=>setRequest(example)}>Use example <ArrowUp size={12}/></button></label><textarea id="customer-request" value={request} onChange={e=>setRequest(e.target.value)} placeholder="We have a production hall 30 × 15 × 6 m. Required airflow is 7,000 m³/h. We are considering two circular fabric ducts approximately 4.5 m above the floor…" disabled={busy}/><div className="request-meta"><FileText size={13}/>Plain language. Structured possibilities.</div><button className="primary-button full" onClick={analyze} disabled={busy}>{busy?<LoaderCircle className="spin" size={17}/>:<Sparkles size={17}/>}Analyze request<ArrowRight size={17}/></button><div className="or-divider"><span/>OR EXPLORE<span/></div><button className="demo-load" onClick={loadDemo} disabled={busy}><span className="demo-icon"><Factory size={22}/></span><span><strong>Load demo project</strong><small>Production hall · 30 × 15 × 6 m</small></span><ArrowRight size={17}/></button><button className="manual-link" onClick={manual} disabled={busy}>Enter parameters manually <ArrowRight size={13}/></button><div className="local-note"><CircleCheck size={15}/><span>Connect OpenAI for live AI. Save your work in Supabase.</span></div></div>:
    <><div className="sidebar-title"><div><SlidersHorizontal size={17}/><h2>Project parameters</h2></div><Tip text="Inspect structured project JSON"><button className="icon-button small" aria-label="View project JSON" onClick={()=>setJsonOpen(true)}><Code2 size={17}/></button></Tip></div><button className="original-request-button" onClick={()=>setRequestOpen(true)}><FileText size={16}/>Původní zadání<ChevronRight size={15}/></button><div className="parameter-scroll">
     <Section title="Space" icon={Factory}><label className="field"><span className="field-label">Room type</span><Picker label="Room type" value={draft.room.type} onChange={v=>update('room.type',v)} options={[['production_hall','Production hall'],['warehouse','Warehouse'],['sports_hall','Sports hall']]}/></label><div className="fields-row three">{field('room.length_m','Length','m',.5)}{field('room.width_m','Width','m',.5)}{field('room.height_m','Height','m',.1)}</div></Section>
     <Section title="Air requirements" icon={Wind} defaultOpen={false}><div className="fields-row">{field('air.airflow_m3h','Total airflow','m³/h',100)}{field('air.static_pressure_pa','Static pressure','Pa',10)}</div><div className="fields-row">{field('air.supply_temperature_c','Supply temp.','°C',1)}{field('air.room_temperature_c','Room temp.','°C',1)}</div>{field('air.occupied_zone_velocity_ms','Occupied-zone velocity','m/s',.05)}</Section>
     <Section title="Fabric ducts" icon={Layers3}><div className="fields-row">{field('ducts.count','Number of ducts','',1)}<label className="field"><span className="field-label">Shape</span><Picker label="Duct shape" value={draft.ducts.shape} onChange={v=>update('ducts.shape',v)} options={[['circular','Circular'],['semicircular','Semicircular']]}/></label></div><div className="fields-row">{field('ducts.diameter_mm','Diameter','mm',50)}{field('ducts.length_m','Length','m',.5)}</div><div className="fields-row">{field('ducts.installation_height_m','Installation height','m',.1)}{field('ducts.spacing_m','Spacing','m',.5)}</div><div className="field"><span className="field-label">Fabric colour <span className="color-name">{formatted('ducts.color',draft.ducts.color)}</span></span><div className="swatches">{colors.map(c=><button key={c} className={'swatch '+(draft.ducts.color===c?'selected':'')} style={{'--swatch':c} as React.CSSProperties} aria-label={'Colour '+formatted('ducts.color',c)} aria-pressed={draft.ducts.color===c} onClick={()=>update('ducts.color',c)} disabled={busy}>{draft.ducts.color===c&&<Check size={14}/>}</button>)}<label className="custom-color" title="Custom fabric colour"><Plus size={15}/><input type="color" aria-label="Custom fabric colour" value={draft.ducts.color} onChange={e=>update('ducts.color',e.target.value)} disabled={busy}/></label></div></div></Section>
     <Section title="Distribution concept" icon={MoveUpRight}><label className="field"><span className="field-label">Distribution type</span><Picker label="Distribution type" value={draft.distribution.type} onChange={v=>update('distribution.type',v)} options={[['microperforation','Microperforation'],['perforation','Perforation'],['small_nozzles','Small nozzles'],['large_nozzles','Large nozzles']]}/></label><div className="fields-row direction-fields"><label className="field"><span className="field-label">Direction</span><Picker label="Direction" value={draft.distribution.direction} onChange={v=>update('distribution.direction',v)} options={[['horizontal','Horizontal'],['downward','Downward'],['angled_down','Angled down']]}/></label>{field('distribution.angle_deg','Angle','°',5)}</div></Section>
    </div><div className="generate-footer">{missing>0&&<p><AlertCircle size={13}/>{missing} air requirements to confirm<Tip text="Missing values are not used for engineering calculations. Confirm them before final design."><button aria-label="About missing parameters" className="plain-help"><CircleHelp size={13}/></button></Tip></p>}<button className="primary-button full" onClick={build} disabled={busy}>{busy?<LoaderCircle className="spin" size={17}/>:<Box size={17}/>} {busy?'Generating…':generated?'Regenerate concept':'Generate concept'}<ArrowRight size={17}/></button></div></>}
   </aside>
   <section className="concept-panel">
    <div className="viewport-toolbar"><div className="viewport-title"><Box size={16}/><strong>Concept viewport</strong><span className="separator"/><span className="subtle">{!generated?'Demo preview':'Live concept'}</span></div><div className="viewport-actions"><button className="text-button compact" onClick={()=>{setPresenting(v=>!v);setTour(!presenting);setDimensions(false);setOccupied(false)}}>{presenting?'Exit presentation':'Present'}<Maximize2 size={15}/></button><button className="text-button compact render-button" onClick={renderStill} disabled={busy||!viewerReady||!status?.blender_ready}><Sparkles size={15}/>Render</button><button className="text-button compact" onClick={exportPNG} disabled={!viewerReady||busy||exporting}><Download size={15}/>PNG</button>{generated&&<a className="text-button compact" href={model.model_url} download="prihoda-concept.glb"><Download size={15}/>GLB</a>}<Tip text="Fullscreen viewport"><button className="icon-button small" aria-label="Fullscreen viewport" onClick={()=>{if(document.fullscreenElement)void document.exitFullscreen().catch(()=>setError('Fullscreen could not be closed.'));else void viewport.current?.requestFullscreen().catch(()=>setError('Fullscreen is unavailable in this browser.'))}}><Maximize2 size={16}/></button></Tip></div></div>
    <div className="viewport" ref={viewport}>
     <Viewer ref={viewer} model={model} project={shown} airflow={airflow} occupied={occupied} dimensions={dimensions} tour={tour} onReady={()=>setReadyModel(model.model_url)} onUnavailable={()=>setReadyModel(null)}/>
     <div className="view-info"><span className="overline">{shown.room.type.replaceAll('_',' ').toUpperCase()}</span><div><b>{shown.room.length_m} × {shown.room.width_m} × {shown.room.height_m}</b><span>m</span></div><small>{shown.ducts.count} fabric ducts <span>·</span> Ø {shown.ducts.diameter_mm} mm <span>·</span> {shown.ducts.installation_height_m} m AFF</small></div>
     <div className="view-top-right"><button className={'tour-button '+(tour?'active':'')} onClick={()=>setTour(v=>!v)}>{tour?'Ⅱ Pause tour':'▶ Cinematic tour'}</button><span className="view-status"><span className={viewerReady?'status-dot':'status-dot amber'}/>{busy?'UPDATING':viewerReady?'INTERACTIVE 3D':'LOADING'}</span><span className="view-revision">{generated?'REV '+String(generationCount).padStart(2,'0'):'DEMO / 01'}</span></div>
     <div className="camera-presets" aria-label="Camera presets">{['Overview','Front','Side','Inside','Detail'].map(p=><button key={p} className={camera===p?'selected':''} aria-pressed={camera===p} onClick={()=>preset(p)}>{p==='Overview'&&<Box size={13}/>} {p}</button>)}</div>
     <div className="viewport-tools"><Tip text="Reset camera"><button aria-label="Reset camera" onClick={()=>preset('Overview')}><Focus size={18}/></button></Tip><span/><Tip text="Zoom in"><button aria-label="Zoom in" onClick={()=>viewer.current?.zoom(.82)}><ZoomIn size={18}/></button></Tip><Tip text="Zoom out"><button aria-label="Zoom out" onClick={()=>viewer.current?.zoom(1.2)}><ZoomOut size={18}/></button></Tip></div>
     <div className="view-guide"><span className="mouse-icon"/><span>Drag to orbit</span><b>·</b><span>Scroll to zoom</span><b>·</b><span>Right-drag to pan</span></div>
     <div className="axis-key"><b className="axis-y">Y</b><span/><b className="axis-z">Z</b><b className="axis-x">X</b></div>
     {active&&dirty&&!busy&&<div className="stale-notice"><AlertCircle size={14}/>Parameters changed. Generate to update this view.</div>}
     {busy&&<div className="generation-overlay" role="status" aria-live="polite"><div className="generation-mark"><LoaderCircle size={22} className="spin"/></div><strong>{stage||'Updating concept'}</strong><small>Your previous concept remains available.</small><div className="generation-steps"><span><Check size={12}/>Validated data</span><ChevronRight size={12}/><span><Box size={12}/>Blender geometry</span></div></div>}
     {changes.length>0&&!busy&&<div className="change-summary" role="status"><div className="change-title"><span className="success-icon"><Check size={16}/></span><div><strong>Concept updated</strong><small>{changes.length} changes applied</small></div><button className="icon-button small" aria-label="Dismiss change summary" onClick={()=>setChanges([])}><X size={15}/></button></div><div className="change-rows">{changes.map(c=><div key={c.path}><span>{labels[c.path]||c.path}</span><span><del>{formatted(c.path,c.old_value)}</del><ArrowRight size={12}/><strong>{formatted(c.path,c.new_value)}</strong></span></div>)}</div><div className="change-actions"><button className="outline-button" onClick={undo}><Undo2 size={14}/>Undo</button><button className="keep-button" onClick={()=>{setChanges([]);setNotice('Changes kept. You can undo the last modification below.')}}>Keep changes<Check size={13}/></button></div></div>}
    </div>
    <div className="visualization-controls"><div className="airflow-controls"><Wind size={16}/><span>Illustrative airflow</span><Tip text="This visualization illustrates the selected distribution concept. It is not a CFD calculation."><button className="plain-help" aria-label="About illustrative airflow"><CircleHelp size={14}/></button></Tip><div className="segmented" role="group" aria-label="Airflow display">{(['off','lines','animated'] as const).map(v=><button key={v} onClick={()=>setAirflow(v)} className={airflow===v?'selected':''} aria-pressed={airflow===v}>{v==='animated'&&<span className="motion-dot"/>}{v[0].toUpperCase()+v.slice(1)}</button>)}</div></div><div className="scene-options"><label><Switch checked={occupied} onCheckedChange={setOccupied} aria-label="Occupied zone"/><span>Occupied zone</span></label><label><Switch checked={dimensions} onCheckedChange={setDimensions} aria-label="Dimensions"/><span>Dimensions</span></label></div></div>
    <div className="command-panel"><div className="command-heading"><div><Sparkles size={17}/><h2>Refine your concept</h2>{previous&&<button className="inline-link undo-link" onClick={undo} disabled={busy}><Undo2 size={13}/>Undo last change</button>}</div><span className="mode-label"><span/>{mode}</span></div><form className={'command-input '+(!active?'inactive':'')} onSubmit={e=>{e.preventDefault();void modify()}}><input ref={commandInput} aria-label="Ask AI to modify the concept" value={command} onChange={e=>setCommand(e.target.value)} disabled={!canModify} placeholder={!active?'Load a project to explore natural-language changes…':!generated?'Generate your concept, then describe a change…':dirty?'Generate updated parameters before a text modification…':'Ask AI to modify the concept…'}/><button type="submit" aria-label="Apply instruction" disabled={!canModify||!command.trim()}><ArrowUp size={19}/></button></form>{receipt?.provider==='openai'&&<div className="ai-receipt"><CircleCheck size={12}/><span>OpenAI · {receipt.model} · {((receipt.latency_ms??0)/1000).toFixed(1)} s</span><span title={receipt.request_id??undefined}>{receipt.request_id?.slice(0,24)}…</span></div>}<div className="suggestions"><span>TRY</span>{suggestions.map(s=><button key={s} disabled={!canModify} onClick={()=>{setCommand(s);commandInput.current?.focus()}}><Plus size={12}/>{s}</button>)}</div></div>
   </section>
  </main>
  {(error||notice)&&<div className={'message-bar '+(error?'error':'info')} role={error?'alert':'status'}><span>{error?<AlertCircle size={17}/>:<Check size={16}/>}</span><p>{error||notice}</p>{error&&<button onClick={usePreview}>Use demo preview</button>}<button className="icon-button small" aria-label="Dismiss message" onClick={()=>{setError('');setNotice('')}}><X size={16}/></button></div>}
  <footer className="statusbar"><div><span className={'status-dot '+(!status?'amber':'')}/><span>{status?(status.ai_mode==='openai'?'OPENAI CONFIGURED':'LOCAL DEMO'):status===undefined?'CONNECTING':'BACKEND OFFLINE'}</span><i/><span className={'status-dot '+(!status?.blender_ready?'amber':'')}/><span>{status?.blender_ready?'3D ENGINE READY':status===undefined?'CHECKING 3D ENGINE':'BLENDER NOT FOUND'}</span></div><p><CircleHelp size={12}/>Concept visualization — not CFD or final engineering design.</p><span className="version">BLENDER + SUPABASE <b>·</b> v2.0</span></footer>
  <Connections open={settings} onClose={()=>{setSettings(false);api<BackendStatus>('/status').then(setStatus).catch(()=>setStatus(null))}}/>
  <Dialog open={requestOpen} onOpenChange={setRequestOpen}><DialogContent className="studio-dialog original-request-dialog"><DialogHeader><DialogTitle>Původní zadání</DialogTitle><DialogDescription>Text, ze kterého tento projekt vznikl. Pozdější úpravy parametrů jej nemění.</DialogDescription></DialogHeader>{draft.original_request?<div className="original-request-text">{draft.original_request}</div>:<p className="original-request-empty">U tohoto projektu nebylo původní textové zadání uložené. Může jít o starší projekt, demo nebo ručně zadaný koncept.</p>}<button className="outline-button" onClick={()=>setRequestOpen(false)}>Zavřít zadání</button></DialogContent></Dialog>
  <Dialog open={jsonOpen} onOpenChange={setJsonOpen}><DialogContent className="studio-dialog json-dialog"><DialogHeader><DialogTitle>Structured project</DialogTitle><DialogDescription>Validated data drives the deterministic Blender generator.</DialogDescription></DialogHeader><pre>{JSON.stringify(draft,null,2)}</pre><button className="primary-button" onClick={downloadJSON}><Download size={16}/>Download project JSON</button></DialogContent></Dialog>
  <Dialog open={!!pngExport} onOpenChange={open=>{if(!open)setPngExport(null)}}><DialogContent className="studio-dialog"><DialogHeader><DialogTitle>PNG ready</DialogTitle><DialogDescription>Your image has been generated and saved locally. Download it for your presentation.</DialogDescription></DialogHeader>{pngExport&&<><img src={pngExport.url} alt="Exported concept view" style={{width:'100%',borderRadius:8}}/><a className="primary-button" href={pngExport.url} download={pngExport.filename}><Download size={16}/>Download PNG</a></>}</DialogContent></Dialog>
 </div></TooltipProvider>
}
