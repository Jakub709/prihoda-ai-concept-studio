# Příprava Railway a GitHub — 15. 9. 2026

- Dockerfile: React build, Python 3.12 a oficiální Linux x64 Blender 4.5.0 s ověřením SHA-256. CPU Cycles, jedna služba na PORT, healthcheck, demo vytvořené při sestavení. Klíče ani uživatelská data nejsou součástí Docker kontextu.
- Production entry point obsluhuje landing page, /studio a sestavené veřejné soubory. /api a /output zůstávají za autentizací. Runtime data používají STUDIO_DATA_DIR=/data a Supabase cesty respektují stejný disk.
- **48 unit testů, TypeScript/Vite build a lint: PASS.** Pokryté jsou také veřejné soubory vs. zdrojový kód, přednost serverových proměnných a cesty na Volume.
- **Skutečný HTTP start přes serve.py: PASS.** Ověřen vlastní PORT, /api/health, / a /studio; testovací proces byl ukončen.
- **Skutečný Blender Cycles CPU: PASS na místním Windows.** Demo vygenerovalo .blend, GLB, manifest a PNG 1600 × 1000. Samotný render trval 2:10.49; obrázek byl vizuálně zkontrolován. Výstup: output/railway-cpu-check/preview.png. Toto není měření výkonu Railway.
- GitHub Actions je připraven pro čisté sestavení, testy, Docker build a skutečný CPU render uvnitř Linux image. Na tomto počítači není Docker, takže Linux image ani tento workflow zde nebyly spuštěné.
- Připraven místní Git repozitář. GitHub CLI hlásí neplatné přihlášení; vzdálený repozitář nebyl vytvořen ani naplněn. Railway dosud nebylo nasazeno.
- OpenAI/Supabase nebyly při této infrastrukturní změně znovu volány. Poslední živé ověření obou služeb je zaznamenané níže; nové nasazení musí projít kontrolou podle DEPLOYMENT.md.

# Původní zadání projektu — 14. 9. 2026, 16:16

- Přidáno tlačítko **Původní zadání** nad parametry a otevření stejného dialogu kliknutím na krok **Request**. Text se zobrazuje beze změn jako prostý text; dlouhé zadání má vlastní posuvník.
- Backend ukládá přesný vstup včetně diakritiky, mezer a odřádkování do `original_request`. AI úpravy jej nemohou přepsat. Pole je součástí parametrů verzí v existujícím JSONB, takže další SQL migrace není potřeba.
- Starší projekty bez zadání se načítají s hodnotou `null` a dostávají vysvětlení. Text není odhadován zpětně z parametrů.
- **45 unit testů, TypeScript/Vite build a lint: PASS.** Nové testy ověřují zachování přesného textu, ochranu před AI přepsáním a načtení starších verzí.
- Živý test přes API na 5174: OpenAI extrakce zachovala přesné zadání; Supabase uložilo a načetlo původní text, historický projekt bez pole vrátil `null`. Testovací projekt `Original request check 2026-09-14 16:15:37`, ID `5907eff7-64cb-4dc3-9962-7c8fc2abdaf9`, verze 1.
- Automatizace prohlížeče nebyla dostupná kvůli chybě jejího runtime, vizuální kontrola nového dialogu tedy neproběhla. Aktualizovaný frontend i backend byly spuštěny na localhostu.

---

# Živé OpenAI a Supabase — 14. 9. 2026, 15:05

**PASS: služby jsou nyní skutečně připojené.** Tento výsledek nahrazuje níže uvedený dřívější stav chybějících klíčů. Podrobný strojový záznam: `output/live-acceptance.json`.

- OpenAI `gpt-5.6-terra`: skutečné ověření, extrakce zákaznického zadání a český příkaz se čtyřmi změnami prošly. Identifikátory odpovědí jsou v protokolu.
- Při kontrole byla opravena chybějící pravidla hodnot v AI zadání: model dříve vracel barvu slovem, a validace ji správně odmítla. Nyní dostává schéma projektu, povolené barvy a pravidla jednotek. Po opravě prošlo také všech 41 unit testů.
- Blender skutečně vytvořil nový model a PNG render (12,08 s).
- Supabase: zápis projektu přes SQL funkci, dvě verze, čtení knihovny, načtení aktuální verze i přesné obnovení parametrů první verze prošly.
- Soukromý bucket potvrzen. GLB, manifest, zdrojový Blender soubor i PNG byly skutečně staženy přes podepsané odkazy. Dotazy s uživatelovým publishable klíčem na obě tabulky i pohled knihovny vrátily 401.
- V knihovně zůstal označený testovací projekt `Studio connection check 2026-09-14 15:04:48`, ID `620180eb-14aa-4578-80a8-aa3f2446c51a`, se dvěma verzemi. Původní lokální aktuální projekt se po testu obnovil.
- Živá kontrola proběhla přes běžící API aplikace na portu 5174. Automatizace prohlížeče v tomto průchodu nebyla dostupná, takže nové cloudové zobrazení v UI nebylo samostatně vizuálně ověřeno. Veřejné nasazení stále nebylo provedeno.

---

# Závěrečná kontrola lokálního režimu — 14. 9. 2026 (před připojením služeb)

**Lokální prezentační web a studio: ověřeno. Veřejné nasazení a živé služby: dosud nedokončeno.** Následující starší záznamy zachovávají historii; aktuální výsledky jsou zde.

- Produkční sestavení TypeScript + Vite a `npm run lint`: PASS po poslední opravě prohlížeče.
- Backend: **41/41 testů PASS**. Nové regrese pokrývají český pokyn „o metr výš“, rozlišení teploty 16 °C od úhlu trysek a kontrolu původu na alternativním místním portu.
- Skutečná generace Blenderu s novým zadáním bez využití cache: PASS, `output/qa-fresh-blender.json` (provedeno 13. 9.). Audit skutečných objektů ověřil dvě bílá potrubí ve výšce 4,5 m s tryskami 30° a tři červená ve výšce 5,5 m s tryskami 35°. Průměr zůstal 600 mm. Vytvořený render 1600 × 1000 byl otevřen a vizuálně zkontrolován. Undo obnovilo původní projekt.
- Prohlížeč po finálním sestavení: ukázkové zadání správně extrahovalo úhel 30°, generace načetla dvě potrubí, přesný český příkaz z prezentace provedl všechny čtyři změny a načetl tři červená potrubí. Undo znovu načetlo dvě bílá potrubí a povolilo export. PNG se skutečně uložilo do `output/exports/prihoda-concept-6968ae19048d.png` a zobrazilo v dialogu **PNG ready**. V tomto průchodu nebyly zachyceny chyby konzole.
- Opravena zaseknutá opakovaná žádost o GLB při návratu k variantě. Prohlížeč má pro každé načtení vlastní požadavky, rušení při změně modelu a časový limit; adresy místních souborů mají jedinečný parametr požadavku. Podepsané cloudové adresy se nemění. Export a další textové úpravy čekají na načtenou geometrii. Při změně scény se uvolňují i její textury.
- Veřejná prezentace byla zkontrolována na desktopu a mobilním rozložení v předchozím průchodu: obrázky, kotvy, přepínač variant, FAQ a vstup do studia. V posledním sestavení byl znovu ověřen vstup z prezentace do studia.
- Přes běžící proxy na portu 5174 vrací nelokální Host pro `/api/projects` i přímý GLB **401**. Místní přístup funguje pouze díky výslovnému vývojovému režimu spouštěče.

## Co zbývá pro živý provoz

`/api/connections` nadále vrací `openai_configured: false` a `supabase_configured: false`. Chybí skutečné přístupové údaje, aplikace migrace do cílového Supabase projektu a živý akceptační test AI → Blender → cloudové uložení → načtení. Implementace je připravená, ale živé AI ani skutečná databáze nejsou tímto protokolem potvrzené. Veřejné nasazení vyžaduje HTTPS, nastavení přístupového kódu, správné směrování chráněných souborů a vypnutí místní výjimky podle README. Web nebyl veřejně publikován.

Aktuální ověřený náhled je **http://127.0.0.1:5174/**. Port 5173 používá jiná aplikace ze složky `Desktop/prihoda2`; tato kontrola se vztahuje na projekt `Desktop/Příhoda/prihoda-ai-concept-studio`.

---

# Ověření Studio 02 — 12. 9. 2026

Aktuální verze má nové prostředí Blenderu, textilní normálovou texturu vloženou do GLB, plynulé kamery, prezentační režim, dialog připojení a implementaci Supabase knihovny s verzemi.

## Ověřeno v této verzi

- TypeScript a produkční sestavení Vite: PASS.
- 29 automatických backendových testů: PASS. Vedle původních testů kontrolují soukromé klíče, odmítnutí cizího původu zápisu, povolený Supabase host, shodu ukládaných parametrů s modelem, privátní cesty souborů, číslo očekávané verze, hlášení konfliktu a chybějící migrace, zachování souborů při nejistém potvrzení zápisu a zapnuté ověřování TLS.
- Kompletní test přes běžící API a skutečný Blender: PASS. Ověřený počet, průměr, výška, barva a úhel trysek před změnou i po změně; Undo obnovilo správný JSON. Výsledek je v `output/e2e-report.json`.
- Generace s PNG v Eevee: 73,83 s pro výchozí model, 67,84 s pro upravený. Geometrie bez PNG v předchozím průchodu vznikla za 6,44 a 7,97 s. Nejde o garantované časy na jiném počítači.
- Čtyři kombinace profilu a distribuce ověřené ze skutečných Blender objektů: PASS, `output/variants-report.json`.
- Sklad a sportovní hala obsahují odlišnou vyexportovanou geometrii; potrubí mají textilní UV souřadnice: PASS, `output/environments-report.json`.
- Prohlížeč: generace ze dvou bílých potrubí, kombinovaný příkaz, viditelná tři červená potrubí, souhrn čtyř změn, Present, pozastavení kamery, Detail, knihovna projektů, přechod do Connections a pravdivé hlášení chybějících klíčů. Při kontrole nebyly zachyceny chyby ani varování konzole.
- SQL migrace je dostupná z aplikace jako skutečný soubor: HTTP 200.
- Tlačítko **Render** v prohlížeči skutečně dokončilo Blender PNG 1600 × 1000 a zobrazilo exportní dialog. Finální scéna po úpravě expozice a kontrastu byla otevřena a vizuálně zkontrolována; kopie všech pěti souborů je v `output/showcase/`.
- Tlačítko **PNG** následně vytvořilo samostatný export aktuálního interaktivního pohledu a zobrazilo jeho náhled.
- Ověřeno HTTPS spojení s OpenAI a Supabase Management API s kontrolou certifikátů Windows. Odpověď 401 bez přístupových údajů potvrzuje transport, nikoliv přihlášení nebo funkční databázi.

## Co není ověřené živě

V konfiguraci stále chybí `OPENAI_API_KEY`, `SUPABASE_URL` a `SUPABASE_SECRET_KEY`. Nebyla aplikována migrace do skutečného Supabase projektu ani provedena placená AI inference, cloudový zápis, obnova cloudové verze či stažení privátních souborů z reálného projektu. Databázové HTTP chování je ověřené pomocí řízených odpovědí, nikoliv náhradní databází vydávanou za Supabase.

`scripts/live_acceptance.py` při spuštění správně skončil `NOT_CONNECTED`. Po připojení provede skutečný AI → Blender → Supabase → načtení a stažení souborů a zapíše `output/live-acceptance.json`. Tento soubor s výsledkem PASS zatím neexistuje.

## Historický záznam verze 1

Následující údaje popisují předchozí verzi z 10.–11. 9.; údaje o Cycles, velikosti modelu a počtu testů se na Studio 02 nevztahují.

Stav k 11. 9. 2026. Projekt je lokální prezentační prototyp podle dodaného zadání.

## Dokončené kontroly

- Produkční sestavení TypeScript + Vite: PASS. Lokální fonty jsou součástí sestavení.
- Backend: 19 automatických testů PASS. Tři další testy kontrolují ukládání PNG, unikátní názvy a odmítnutí chybných nebo příliš velkých obrázků. Zahrnují validaci, extrakci parametrů, požadovaný kombinovaný příkaz, české varianty, nepovolené a zastaralé patche, chybný JSON, chybějící Blender, selhání procesu a exportu, timeout, nedostupné AI API a obnovení uloženého projektu z cache.
- Spouštěč start.py: spuštěn z připraveného Python prostředí; frontend a backend odpověděly na lokálních portech 5173 a 8000.
- Celý scénář přes frontendovou proxy a skutečný Blender: PASS, viz output/e2e-report.json. Extrakce ukázkového požadavku, generace, kombinovaná změna, načtení skutečného GLB a Undo včetně projects/current_project.json.
- Audit .blend před změnou: 2 potrubí, výška 4,5 m, průměr 600 mm, bílý materiál, trysky 30°, 56 trysek a 56 trajektorií.
- Audit .blend po změně: 3 potrubí, výška 5,5 m, průměr 600 mm, červený materiál, trysky 35°, 84 trysek a 84 trajektorií.
- Audit kontroluje skutečné Blender objekty, jejich rozměry, polohy, materiály a orientaci. Neověřuje pouze vstupní JSON.
- Browser QA z 10. 9. 2026: zobrazení aplikace při 1440 × 900 a 1920 × 1080; načtení dema, Generate concept, kombinovaná textová změna a viditelná nová geometrie, Undo, kamera Inside a vypnutí proudění. Následně byla upravena velikost ovládacích prvků a sbalen výchozí panel Air parameters; produkční sestavení po úpravě prošlo.

## Rozsah a omezení ověření

Dodatečné kontroly také prošly:

- Čtyři varianty skutečných .blend a GLB: půlkruhová perforace horizontálně, půlkruhová mikroperforace svisle dolů, kruhové malé trysky pod úhlem 40° a kruhové velké trysky svisle dolů. Počet 1, průměr 800 mm, délka 18 m, výška 4 m. Profil je ověřen ze světových souřadnic vrcholů. Výsledky: output/variants-report.json.
- Devět lokálních HTTP cest včetně produkčního JavaScriptu, CSS, fontu s českými znaky, loga, GLB, manifestu a PNG: PASS, viz output/http-audit.json.
- Finální Blender render: PASS, viz output/final-render/preview.png. PNG 1280 × 800 bylo otevřeno a vizuálně zkontrolováno; tři červená potrubí, konstrukce haly, stroje, postavy a ilustrativní trajektorie jsou viditelné. CPU render při souběžných testech trval 6 min 57 s. Stejná scéna je uložena jako .blend a GLB.

Po obnovení spojení 11. 9. proběhla i závěrečná kontrola přímo v prohlížeči: 1440 × 900 a 1920 × 1080, generování, přesný kombinovaný příkaz, viditelná tři červená potrubí ve výšce 5,5 m, souhrn čtyř změn a Undo zpět na dvě bílá potrubí ve výšce 4,5 m. Na úzkém panelu bylo ověřeno skládání úvodního formuláře. Všechny kombinace mobilních rozlišení a kamer nebyly samostatně testovány.

Původní stahování PNG přes datový/blob odkaz vestavěný prohlížeč nepotvrdil. Export byl doplněn o skutečné uložení na lokálním backendu a dialog s hotovým obrázkem. Tlačítko PNG nyní ověřeně vytvořilo output/exports/prihoda-concept-ca7fba79c3a5.png a zobrazilo jeho náhled. Nativní stažení do složky Downloads není podmínkou tohoto exportu.

OpenAI provider je otestován lokálně s řízenými odpověďmi včetně strict JSON schématu a odmítnutí. Živé volání OpenAI nebylo bez API klíče testováno. Demo Mode funguje bez externí služby.

První generace při dnešní kontrole odhalily časový limit CPU renderu a zpomalení při opakovaných operacích Blenderu. Generátor nyní vytváří základní mesh objekty přímo; timeout geometrie je 150 s a explicitního PNG renderu 600 s. Výsledný render používá Cycles, 8 vzorků a rozlišení 1280 × 800. Interaktivní generace vytváří GLB bez čekání na PNG.

Časy v output/e2e-report.json zahrnují odpovědi z cache; nejsou měřením studeného startu Blenderu.

## Reprodukce

Spusťte START.cmd. Potom ze složky aplikace:

    ..\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
    npm run build
    ..\.venv\Scripts\python.exe -X utf8 -m tests.e2e
    ..\.venv\Scripts\python.exe -X utf8 -m tests.variants

Volitelný úplný test včetně CPU renderů obou scén:

    ..\.venv\Scripts\python.exe -X utf8 -m tests.e2e --render

Při testech neměňte generátor ani současně projekt v prohlížeči. Generátor je součástí klíče cache a úprava zdrojového kódu během testu záměrně vytvoří jiný identifikátor výsledku.
# Veřejná prezentace a oddělené studio — 13. 9. 2026

- `/` otevírá novou českou prezentaci s originálním logem, skutečnými rendery z Blenderu, přepínačem variant, postupem práce, funkcemi a FAQ. Veřejná stránka nevolá generování ani projektovou knihovnu.
- `/studio` před načtením 3D části ověřuje serverové přihlášení. Veřejná konfigurace vyžaduje HTTPS původ a tajný přístupový kód; bez konfigurace je přístup uzavřený. `start.py` výslovně povoluje pouze místní vývojovou výjimku.
- **38/38 unit testů prošlo**, včetně 9 nových testů přístupu: zamčený výchozí server, ochrana API i souborů, přihlášení/odhlášení, atributy cookie, chybný kód a limit pokusů, změněná/propadlá/zneplatněná relace, cizí původ požadavků, nemožnost měnit klíče vzdáleně a podmínky místní výjimky.
- Produkční sestavení TypeScript + Vite prošlo. Vstupní JavaScript má přibližně 214 kB; samostatný balík studia (893 kB) se načítá až po ověření přístupu.
- V prohlížeči ověřeno rozložení 1440 × 900 a 390 × 844, přepnutí obou variant a jejich parametrů, otevření FAQ, přechod do místního studia a načtení interaktivního 3D modelu bez konzolových chyb.
- Na běžícím FastAPI i přes Vite proxy ověřeny požadavky s nelokálním Host: projekty i přímá adresa GLB vracejí **401** a `Cache-Control: no-store`. Proxy výslovně zachovává původní Host. Na `preview.localhost:5173/studio` ověřena skutečná zamčená obrazovka v prohlížeči, zatímco `127.0.0.1:5173/studio` zůstává v povoleném místním režimu.
- Tato kontrola nezahrnovala veřejné nasazení ani živé připojení OpenAI/Supabase; jejich konfigurace se tímto úkolem neměnila. Provozní podmínky přístupové brány a proxy jsou popsané v README.
