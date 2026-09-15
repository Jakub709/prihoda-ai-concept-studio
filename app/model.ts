export type Project = {
 project_name:string;
 original_request?:string|null;
 room:{type:string;length_m:number;width_m:number;height_m:number};
 air:{airflow_m3h:number|null;supply_temperature_c:number|null;room_temperature_c:number|null;static_pressure_pa:number|null;occupied_zone_velocity_ms:number|null};
 ducts:{count:number;shape:string;diameter_mm:number;length_m:number;installation_height_m:number;spacing_m:number;color:string};
 distribution:{type:string;direction:string;angle_deg:number};
 visualization:{airflow_mode:'off'|'lines'|'animated';show_occupied_zone:boolean;show_dimensions:boolean;environment:string};
}
export type Change={path:string;old_value:string|number|boolean|null;new_value:string|number|boolean|null}
export type ModelResult={id:string;model_url:string;manifest_url:string;preview_url?:string|null;blend_url?:string}
export type ProjectValue=string|number|boolean|null
export type Receipt={provider:string;model?:string;latency_ms?:number;request_id?:string|null}
export type BackendStatus={ok:boolean;ai_mode:string;blender_ready:boolean;blender_name?:string}
export type ParsedProject={project:Project;extracted:string[];unconfirmed:string[];provider:string;receipt?:Receipt}
export type ModifiedProject={project:Project;changes:Change[];receipt:Receipt}
export type GenerationJob=Partial<ModelResult>&{id:string;state:'queued'|'running'|'ready'|'error';stage:string;error?:string}
export type SavedIdentity={project_id:string;version:number;latest_version?:number;name?:string}
export type SavedProject=SavedIdentity&{project:Project;model:ModelResult}
export type LibraryItem={id:string;name:string;latest_version:number;updated_at:string;room:Project['room'];ducts:Project['ducts']}
export type LibraryVersion={id:string;version:number;note:string;created_at:string}
export type ConnectionSettings={openai_configured:boolean;openai_model:string;supabase_configured:boolean;supabase_url:string}
export type ConnectionChecks=Record<'openai'|'supabase',{connected:boolean;message:string;receipt?:Receipt}>
export const DEMO:Project={
 project_name:'Production Hall Demo',
 room:{type:'production_hall',length_m:30,width_m:15,height_m:6},
 air:{airflow_m3h:7000,supply_temperature_c:16,room_temperature_c:22,static_pressure_pa:null,occupied_zone_velocity_ms:null},
 ducts:{count:2,shape:'circular',diameter_mm:600,length_m:22,installation_height_m:4.5,spacing_m:6,color:'#eeeeee'},
 distribution:{type:'large_nozzles',direction:'angled_down',angle_deg:30},
 visualization:{airflow_mode:'animated',show_occupied_zone:false,show_dimensions:true,environment:'production_hall'}
}
export const DEMO_MODEL:ModelResult={id:'demo',model_url:'/demo/model.glb',manifest_url:'/demo/manifest.json',preview_url:'/demo/preview.png'}
export const labels:Record<string,string>={
 'ducts.count':'Duct count','ducts.diameter_mm':'Diameter','ducts.color':'Colour','ducts.installation_height_m':'Installation height',
 'ducts.length_m':'Duct length','ducts.spacing_m':'Spacing','ducts.shape':'Shape','distribution.angle_deg':'Nozzle angle',
 'distribution.direction':'Direction','distribution.type':'Distribution type','room.length_m':'Hall length','room.width_m':'Hall width',
 'room.height_m':'Hall height','room.type':'Room type','air.airflow_m3h':'Airflow','air.static_pressure_pa':'Static pressure',
 'air.supply_temperature_c':'Supply temperature','air.room_temperature_c':'Room temperature','air.occupied_zone_velocity_ms':'Occupied-zone velocity'
}
export function valueAt(p:Project,path:string):ProjectValue{const [s,k]=path.split('.');const section=p[s as keyof Project];if(typeof section!=='object'||!section||!Object.hasOwn(section,k))throw new Error('Unknown project parameter');return (section as Record<string,ProjectValue>)[k]}
export function setAt(p:Project,path:string,value:ProjectValue):Project{valueAt(p,path);const copy=structuredClone(p);const [s,k]=path.split('.');const section=copy[s as keyof Project];if(!section||typeof section!=='object')throw new Error('Unknown project section');Object.assign(section,{[k]:value});return copy}
export function formatted(path:string,v:ProjectValue){
 if(v===null)return 'Missing'
 const colors:Record<string,string>={'#eeeeee':'White','#d71920':'Red','#2874ad':'Blue','#475c50':'Green','#50565d':'Grey','#25282c':'Black'}
 if(path==='ducts.color'&&typeof v==='string')return colors[v]||v
 if(typeof v==='string')return v.replaceAll('_',' ')
 const suffix=path.endsWith('_mm')?' mm':path.endsWith('_m')?' m':path.endsWith('_deg')?'°':path.endsWith('_m3h')?' m³/h':path.endsWith('_c')?' °C':path.endsWith('_pa')?' Pa':''
 return v+suffix
}
export async function api<T=unknown>(path:string,body?:unknown):Promise<T>{
 let response:Response
 try{response=await fetch('/api'+path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(path.startsWith('/projects')||path==='/connections/test'?180000:45000)})}
 catch{throw new Error('The local service is unavailable. Start the backend, then try again. You can still explore the demo preview.')}
 let data:unknown
 try{data=await response.json()}
 catch{throw new Error('The local service did not respond correctly. Check that the backend is running, then try again.')}
 if(response.status===401)window.dispatchEvent(new Event('studio-session-expired'))
 if(!response.ok){const detail=typeof data==='object'&&data!==null&&'detail' in data?data.detail:null;throw new Error(typeof detail==='string'?detail:'Check your parameters and try again.')}
 return data as T
}
