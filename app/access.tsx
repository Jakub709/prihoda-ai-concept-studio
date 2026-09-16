import { lazy, Suspense, useCallback, useEffect, useState, type SubmitEvent } from 'react'
import { ArrowLeft, ArrowRight, LoaderCircle, LockKeyhole, LogOut } from 'lucide-react'
import './landing.css'

const Studio = lazy(() => import('./page'))
type Session = { authenticated: boolean; configured: boolean; local: boolean; setup_issues?: string[] }

export default function StudioAccess() {
 const [session,setSession] = useState<Session|null>(null)
 const [code,setCode] = useState('')
 const [error,setError] = useState('')
 const [checking,setChecking] = useState(true)
 const [busy,setBusy] = useState(false)
 useEffect(()=>{document.documentElement.lang=session?.authenticated?'en':'cs'},[session?.authenticated])
 const check = useCallback(async () => {
  setChecking(true);setError('')
  try {
   const response = await fetch('/api/auth/session',{cache:'no-store',signal:AbortSignal.timeout(15000)})
   if(!response.ok)throw new Error()
   const data:Session = await response.json()
   if(typeof data.authenticated!=='boolean'||typeof data.configured!=='boolean'||typeof data.local!=='boolean')throw new Error()
   setSession(data)
   return data
  } catch { setError('Studio se teď neozývá. Zkontrolujte připojení a zkuste to znovu.') }
  finally { setChecking(false) }
 },[])
 useEffect(()=>{
  void check()
  const expired = () => {setSession(s=>s?{...s,authenticated:false}:s);setError('Přihlášení vypršelo. Zadejte prosím znovu svůj přístupový kód.')}
  window.addEventListener('studio-session-expired',expired)
  return ()=>window.removeEventListener('studio-session-expired',expired)
 },[check])
 async function login(event:SubmitEvent<HTMLFormElement>) {
  event.preventDefault();setBusy(true);setError('')
  try {
   const response=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code}),signal:AbortSignal.timeout(15000)})
   const data=await response.json()
   if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Přihlášení se nezdařilo. Zkuste to znovu.')
   // Verify that the browser actually accepted the secure session cookie.
   setCode('')
   const verified=await check()
   if(verified&&!verified.authenticated)throw new Error('Přihlášení se neuložilo. Povolte prosím nezbytné cookies pro tuto stránku a zkuste to znovu.')
  } catch(e) {setError(e instanceof Error&&e.name!=='TypeError'&&e.name!=='TimeoutError'?e.message:'Přihlášení se nezdařilo. Zkontrolujte připojení a zkuste to znovu.')}
  finally {setBusy(false)}
 }
 async function logout() {
  setBusy(true)
  try {
   const response=await fetch('/api/auth/logout',{method:'POST',signal:AbortSignal.timeout(15000)})
   if(!response.ok)throw new Error()
   setSession(s=>s?{...s,authenticated:false}:s);setError('')
  } catch {setError('Odhlášení se nepodařilo. Zkuste to znovu.')}finally{setBusy(false)}
 }
 if(session?.authenticated) return <><Suspense fallback={<AccessLoading/>}><Studio allowSettings={session.local}/></Suspense>{!session.local&&<div className="access-session"><button onClick={logout} disabled={busy}><LogOut size={12}/>{busy?'Odhlašuji…':'Odhlásit se'}</button>{error&&<p className="access-error" role="alert">{error}</p>}</div>}</>
 return <div className="access-page">
  <aside className="access-story"><a href="/"><ArrowLeft size={15}/>Zpět na úvod</a><div><h2>Vaše zadání.<br/>Nová perspektiva.</h2><img src="/landing/three-red-ducts.png" alt="Koncept textilního potrubí ve výrobní hale" width="1600" height="1000"/></div><p>PŘÍHODA / AI CONCEPT STUDIO</p></aside>
  <main className="access-panel"><a className="access-logo" href="/" aria-label="PŘÍHODA – úvod"><img src="/brand/prihoda-logo.svg" alt="PŘÍHODA" width="146" height="50"/></a>
   <p className="landing-eyebrow"><LockKeyhole size={14}/>SOUKROMÝ PRACOVNÍ PROSTOR</p>
   <h1>{checking?'Připravujeme studio…':'Vítejte ve studiu.'}</h1>
   {checking?<p role="status"><LoaderCircle className="spin" size={20}/> Ověřujeme přístup.</p>:<>
    <p>{session?.configured?'Zadejte přístupový kód, který jste dostali od správce. Vaše projekty na vás čekají uvnitř.':session?'Studio je určené pozvaným uživatelům. Přístup zatím není aktivovaný; podrobnosti vám poskytne správce.':'Pracovní studio není momentálně dostupné. Veřejnou ukázku si můžete dál prohlédnout na úvodní stránce.'}</p>
    {session?.configured?<form onSubmit={login}><label htmlFor="studio-code">Přístupový kód</label><input id="studio-code" name="password" type="password" autoComplete="current-password" value={code} onChange={e=>setCode(e.target.value)} required maxLength={256} aria-describedby={error?'access-error':undefined}/>{error&&<p className="access-error" id="access-error" role="alert">{error}</p>}<button className="landing-button" type="submit" disabled={busy||!code}>{busy?<LoaderCircle size={17} className="spin"/>:<LockKeyhole size={15}/>} {busy?'Přihlašuji…':'Vstoupit do studia'}<ArrowRight size={17}/></button></form>:<>{error&&<p className="access-error" role="alert">{error}</p>}<div className="access-actions"><button className="landing-button" onClick={()=>void check()}>Zkusit znovu<ArrowRight size={16}/></button><a className="landing-text-link" href="/#ukazka">Prohlédnout ukázku</a></div></>}
    {!session?.configured&&session?.setup_issues?.map(issue=><p className="access-error" key={issue}>{issue}</p>)}
    <p className="access-notice">Nemáte přístup? Obraťte se na člověka, který vám studio představil.</p>
    <a className="landing-text-link" href="/"><ArrowLeft size={14}/>Zpět na úvodní stránku</a>
   </>}
  </main>
 </div>
}

function AccessLoading(){return <div className="access-page"><main className="access-panel"><p role="status"><LoaderCircle size={22} className="spin"/> Načítáme 3D studio…</p></main></div>}
