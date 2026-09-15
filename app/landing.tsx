import { useState } from 'react'
import { ArrowDown, ArrowRight, ArrowUpRight, Box, Check, Download, Layers3, LockKeyhole, MessageSquare, Move3D, Plus, Wind } from 'lucide-react'
import './landing.css'

const variants = [
 { name: 'Původní koncept', image: '/demo/preview.png', count: '02', color: 'Bílá', height: '4,5 m', angle: '30°', label: 'Dvě bílé větve textilního potrubí ve výrobní hale' },
 { name: 'Upravený koncept', image: '/landing/three-red-ducts.png', count: '03', color: 'Červená', height: '5,5 m', angle: '35°', label: 'Tři červené větve potrubí zavěšené o metr výše ve stejné výrobní hale' },
]

export default function Landing() {
 const [variant, setVariant] = useState(1)
 const scene = variants[variant]
 return <div className="landing">
  <a className="landing-skip" href="#obsah">Přejít na obsah</a>
  <header className="landing-header">
   <a className="landing-brand" href="/" aria-label="PŘÍHODA – úvod"><img src="/brand/prihoda-logo.svg" alt="PŘÍHODA" width="144" height="48"/><span>AI CONCEPT STUDIO</span></a>
   <nav aria-label="Hlavní navigace"><a href="#moznosti">Co studio umí</a><a href="#jak-to-funguje">Jak to funguje</a><a href="#ukazka">Ukázka</a></nav>
   <a className="landing-entry" href="/studio"><LockKeyhole size={14}/><span>Vstup do studia</span><ArrowUpRight size={17}/></a>
  </header>

  <main id="obsah">
   <section className="landing-hero" aria-labelledby="hero-title">
    <div className="landing-hero-copy">
     <p className="landing-eyebrow"><span/>NOVÝ POHLED NA DISTRIBUCI VZDUCHU</p>
     <h1 id="hero-title">Dejte svému<br/>návrhu <em>prostor.</em></h1>
     <p className="landing-lead">Z popisu haly do 3D konceptu textilního potrubí. Prozkoumejte návrh, upravte ho jednou větou a ukažte zákazníkovi, co máte na mysli.</p>
     <div className="landing-hero-actions"><a className="landing-button" href="#ukazka">Podívat se na ukázku<ArrowDown size={18}/></a><a className="landing-text-link" href="#jak-to-funguje">Jak to funguje<ArrowRight size={16}/></a></div>
     <div className="landing-hero-note"><span className="landing-note-line"/><span>Vaše zadání. Vaše parametry. Společná představa.</span></div>
    </div>
    <div className="landing-hero-art">
     <div className="landing-art-label"><span><i/>CONCEPT / 01</span><Box size={19}/></div>
     <img src="/landing/three-red-ducts.png" alt="3D koncept distribuce vzduchu: tři červená textilní potrubí v otevřené výrobní hale" width="1600" height="1000" fetchPriority="high"/>
     <div className="landing-art-caption"><span>Výrobní hala<span>30 × 15 × 6 m</span></span><span className="landing-render-tag">RENDER ZE STUDIA<ArrowUpRight size={15}/></span></div>
    </div>
   </section>

   <div className="landing-proof" aria-label="Hlavní možnosti"><span><MessageSquare size={19}/>Zadání běžným jazykem</span><span><Move3D size={20}/>Skutečný prostorový model</span><span><Layers3 size={20}/>Varianty, které můžete porovnat</span></div>

   <section className="landing-process landing-section" id="jak-to-funguje" aria-labelledby="process-title">
    <div className="landing-section-heading"><div><p className="landing-eyebrow">01 / OD MYŠLENKY K NÁVRHU</p><h2 id="process-title">Méně vysvětlování.<br/>Více společné představy.</h2></div><p>Studio propojuje zadání, parametry a vizualizaci v jednom místě. Aby se rozhovor o řešení mohl posunout dál.</p></div>
    <div className="landing-steps">
     <article><span className="landing-step-number">01 <span/></span><MessageSquare size={25}/><h3>Popište prostor</h3><p>Vložte požadavek zákazníka. Rozměry haly, průtok vzduchu a představu o potrubí. Chybějící údaje doplníte v přehledných parametrech.</p></article>
     <article><span className="landing-step-number">02 <span/></span><Box size={25}/><h3>Prohlédněte si koncept</h3><p>Vytvořte 3D scénu s halou, potrubím a vyústkami. Otočte ji, přibližte detail a podívejte se na uspořádání z více úhlů.</p></article>
     <article><span className="landing-step-number">03 <span/></span><Wind size={25}/><h3>Rozvíjejte návrh</h3><p>Změňte barvu, počet větví nebo výšku zavěšení. Příkazem v chatu či ručně. Nová varianta vychází z vašeho aktuálního konceptu.</p></article>
    </div>
   </section>

   <section className="landing-showcase" id="ukazka" aria-labelledby="showcase-title">
    <div className="landing-section-heading"><div><p className="landing-eyebrow">02 / PODÍVEJTE SE NA ZMĚNU</p><h2 id="showcase-title">Jedna věta.<br/>Nová perspektiva.</h2></div><p>Stejná hala, jiná varianta řešení. Přepněte mezi dvěma skutečnými rendery vytvořenými ve studiu.</p></div>
    <div className="landing-demo">
     <div className="landing-demo-visual">
      <div className="landing-demo-top"><span>VÝROBNÍ HALA / 30 × 15 × 6 m</span><span>UKÁZKOVÝ PROJEKT</span></div>
      <div className="landing-demo-images">{variants.map((v,i)=><img key={v.name} src={v.image} alt={v.label} width="1600" height="1000" loading="lazy" className={i===variant?'is-visible':''} aria-hidden={i!==variant}/>)}</div>
      <div className="landing-demo-toggle" role="group" aria-label="Varianta ukázky">{variants.map((v,i)=><button key={v.name} aria-pressed={variant===i} onClick={()=>setVariant(i)}>{i===1?<span className="landing-red-dot"/>:<span className="landing-white-dot"/>}{v.name}</button>)}</div>
     </div>
     <div className="landing-demo-detail">
      <p className="landing-eyebrow"><MessageSquare size={15}/>POKYN K ÚPRAVĚ</p>
      <blockquote>„Použij tři červená potrubí, posuň je o metr výš a natoč trysky 35° dolů.“</blockquote>
      <div className="landing-variant-label" aria-live="polite"><Check size={15}/>{scene.name}</div>
      <dl><div><dt>Počet větví</dt><dd>{scene.count}</dd></div><div><dt>Barva potrubí</dt><dd><i className={variant===1?'landing-red-dot':'landing-white-dot'}/>{scene.color}</dd></div><div><dt>Výška zavěšení</dt><dd>{scene.height}</dd></div><div><dt>Úhel trysek</dt><dd>{scene.angle}</dd></div></dl>
      <p className="landing-demo-footnote">Předem vytvořená ukázka. V přihlášeném studiu pracujete s vlastním zadáním.</p>
     </div>
    </div>
   </section>

   <section className="landing-capabilities landing-section" id="moznosti" aria-labelledby="capabilities-title">
    <div className="landing-section-heading"><div><p className="landing-eyebrow">03 / VŠE PRO SROZUMITELNÝ KONCEPT</p><h2 id="capabilities-title">Od prvního pohledu<br/>k další schůzce.</h2></div><p>Nástroje, které pomáhají návrh prozkoumat, představit i uchovat pro další práci.</p></div>
    <div className="landing-features">
     <article><Move3D size={27}/><h3>Prostor pod kontrolou</h3><p>Pohled zepředu, ze strany i zevnitř. Rozměry, detaily vyústek a ilustrativní proudění přímo ve 3D scéně.</p><span>OTÁČENÍ · DETAILY · ROZMĚRY</span></article>
     <article><Download size={27}/><h3>Připraveno k prezentaci</h3><p>Režim prezentace s plynulou kamerou, PNG náhled a render z Blenderu. Výstupy pro další rozhovor se zákazníkem.</p><span>PREZENTACE · PNG · 3D MODEL</span></article>
     <article><Layers3 size={27}/><h3>Každá varianta má své místo</h3><p>Po připojení cloudové knihovny uložíte projekt i jeho verze. K parametrům a modelu se vrátíte při další úpravě.</p><span>PROJEKTY · HISTORIE · NÁVRAT K VERZI</span></article>
    </div>
   </section>

   <section className="landing-faq landing-section" aria-labelledby="faq-title">
    <div><p className="landing-eyebrow">JEŠTĚ NEŽ VSTOUPÍTE</p><h2 id="faq-title">Dobré vědět.</h2><p>Jasná představa o tom,<br/>k čemu studio slouží.</p></div>
    <div className="landing-faq-list">
     <details><summary>Pro koho je studio určené?<Plus size={20}/></summary><p>Pro tým, který se zákazníkem rozvíjí první koncept distribuce vzduchu. Pomáhá ukázat uspořádání potrubí v prostoru a porovnat varianty ještě před detailním technickým návrhem.</p></details>
     <details><summary>Může do studia vstoupit každý?<Plus size={20}/></summary><p>Tato stránka je veřejná prezentace. Pracovní studio je určené pozvaným uživatelům a při veřejném nasazení vyžaduje přístupový kód od správce. Projekty a generování jsou chráněné na serveru.</p></details>
     <details><summary>Je zobrazené proudění technický výpočet?<Plus size={20}/></summary><p>Proudění slouží k názornému vysvětlení směru distribuce vzduchu. Studio vytváří konceptuální vizualizace; nenahrazuje CFD výpočet ani finální technický návrh.</p></details>
     <details><summary>Jak funguje AI a ukládání projektů?<Plus size={20}/></summary><p>Připojené studio zpracovává pokyny přes AI a ukládá projekty do soukromé cloudové knihovny. Bez připojených služeb lze pracovat v označeném demo režimu s omezenými pokyny; cloudové ukládání v něm není dostupné.</p></details>
    </div>
   </section>

   <section className="landing-cta"><div><p className="landing-eyebrow">PŘÍHODA / AI CONCEPT STUDIO</p><h2>Začněte zadáním.<br/>Pokračujte v prostoru.</h2></div><div><a className="landing-button landing-button-light" href="/studio">Vstoupit do studia<ArrowUpRight size={20}/></a><p><LockKeyhole size={13}/>Soukromý pracovní prostor pro pozvané</p></div></section>
  </main>
  <footer className="landing-footer"><a href="/" aria-label="PŘÍHODA – úvod"><img src="/brand/prihoda-logo.svg" alt="PŘÍHODA" width="116" height="40"/></a><span>AI Concept Studio · Prostor pro lepší představu.</span><a href="#obsah">Zpět nahoru<ArrowUpRight size={14}/></a></footer>
 </div>
}
