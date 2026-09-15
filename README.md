# PŘÍHODA AI Concept Studio

**Nasazení na Railway přes GitHub:** postup, proměnné a ověření jsou v [DEPLOYMENT.md](DEPLOYMENT.md). Docker spouští celý web i API a používá Blender Cycles na CPU; místní spuštění zůstává dostupné.

Prezentační aplikace podle dodaného PDF, rozšířená na Studio 02. React + TypeScript, FastAPI, skutečná geometrie z Blenderu, integrace OpenAI a knihovna projektů v Supabase. Rozhraní běží lokálně; po připojení se textové požadavky zpracovávají přes OpenAI a uložené projekty putují do soukromého Supabase úložiště.

**Konceptuální vizualizace, nikoli CFD ani finální technický návrh.**

## Veřejná prezentace a soukromé studio

Na `/` je česká úvodní stránka: představení produktu, skutečné rendery z Blenderu s přepínáním dvou variant, pracovní postup, možnosti a FAQ. Stránka nevolá AI ani knihovnu projektů. 3D prohlížeč se načítá až po vstupu na `/studio`. Logo ve studiu vrací na prezentaci.

Přístup je určený jednomu uzavřenému týmu se společným přístupovým kódem. API, dokumentace API a celé `/output/` kontrolují přihlášení na serveru. Pouhé otevření adresy modelu nebo odeslání požadavku na generování přístup neobejde. Veřejné obrázky a model v `public/demo/` jsou záměrně ukázkové podklady bez zákaznických dat.

**Před veřejným nasazením** nastavte na backendu `STUDIO_PUBLIC_ORIGIN` na přesnou HTTPS adresu webu bez cesty a `STUDIO_ACCESS_CODE` na náhodný tajný kód o 16–256 znacích. Kód patří pouze do serverového prostředí nebo ignorovaného `.env`, nikdy do Vite proměnných či repozitáře. `STUDIO_LOCAL_DEVELOPMENT` musí být na veřejném serveru `0`. Bez platné konfigurace zůstává studio zamčené. Web v této úpravě nebyl publikován.

Hostování musí pod jednou HTTPS adresou obsluhovat frontend z `dist/`, směrovat `/api/`, `/output/`, `/docs`, `/redoc` a `/openapi.json` přes FastAPI a pro `/studio` vracet `dist/index.html`. **Nevystavujte složku `output/` přímo jako statický adresář hostingu** — obešlo by to ověření na backendu. Soukromé odpovědi mají `Cache-Control: no-store`; proxy toto pravidlo musí zachovat. Backend vystavujte pouze za důvěryhodnou proxy. Spouštěč `START.cmd` / `start.py` je výhradně pro místní ukázku, nikoli pro veřejné hostování.

Přihlášení používá podepsanou `HttpOnly; Secure; SameSite=Strict` cookie na 8 hodin, kontrolu původu zápisů a omezení chybných pokusů. Změna kódu zneplatní všechna přihlášení; tlačítko **Odhlásit se** odstraní cookie z daného prohlížeče. Omezení pokusů je v paměti procesu (za proxy společné pro tým); při nasazení s více procesy doplňte společný limit na proxy. Nejde o individuální uživatelské účty ani oddělení dat mezi zákazníky: přihlášený tým sdílí knihovnu. Nastavení OpenAI a Supabase se ve veřejném režimu mění pouze na serveru.

Místní `start.py` výslovně povolí vývojový režim pro služby vázané na `127.0.0.1`, takže na tomto počítači funguje vstup bez kódu. Výjimka vyžaduje lokálního klienta i lokální adresu a odmítá požadavky s hlavičkami proxy. Jakmile je nastaven veřejný původ nebo přístupový kód, lokální výjimka se vypne. `/api/health` zůstává veřejný pouze pro kontrolu běhu služby; nevrací projekty, připojení ani klíče.

## Studio 02 — připojení živých služeb

Otevřete ozubené kolečko **System settings** vpravo nahoře. V dialogu **Connect your studio** zadejte OpenAI API key, model, Supabase Project URL a serverový secret key. Tlačítko **Save & verify connections** provede skutečné ověření obou služeb. Tajné hodnoty se ukládají do ignorovaného souboru `.env` na backendu; API je nevrací a frontend je neukládá do localStorage. Prázdné pole při uložení ponechá již zadaný klíč.

Při prvním připojení Supabase spusťte soubor `supabase/migrations/202609120001_prihoda_studio.sql` v SQL Editoru cílového projektu. SQL lze stáhnout také přímo z dialogu připojení. Migrace přidává tabulky `prihoda_projects` a `prihoda_versions`, pohled knihovny, transakční funkci pro ukládání a soukromý bucket `prihoda-concepts`. Zapíná RLS; anonymní a přihlášené klientské role nemají přístup. Operace zajišťuje lokální server.

Alternativou SQL Editoru je skript `scripts/setup_supabase.py`: vyžaduje navíc `SUPABASE_ACCESS_TOKEN` pro Management API a použije pouze projekt určený `SUPABASE_URL`.

    ..\.venv\Scripts\python.exe scripts/setup_supabase.py

**Projects** načítá knihovnu z Postgresu. **Save project / Save v…** ukládá parametry, aktuální PNG, GLB a zdrojový `.blend` do privátního Storage. Historie otevře libovolnou předchozí verzi. Současné úpravy jsou chráněné kontrolou čísla poslední verze; starší zápis nemůže tiše přepsat novější. Po otevření cloudové verze a dalších změnách nejprve použijte **Regenerate concept**.

OpenAI odpovědi používají strict JSON schema a procházejí validací. Po skutečném AI požadavku se zobrazuje model, doba odpovědi a identifikátor požadavku. Konfigurace klíče sama o sobě není ověřením dostupnosti. Bez klíče je výslovně označený **DEMO MODE** s omezeným lokálním parserem. Bez Supabase nelze předstírat cloudové uložení: aplikace zobrazí potřebné připojení.

Technické zdroje: [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [Supabase API keys](https://supabase.com/docs/guides/getting-started/api-keys), [Supabase zabezpečení API](https://supabase.com/docs/guides/api/securing-your-api), [Management API SQL](https://supabase.com/docs/reference/api/v1-run-a-query).

Připojení používá důvěryhodné certifikáty operačního systému a zachovává ověřování certifikátů i názvu serveru. Tím je řešená kompatibilita se spravovaným prostředím Windows.

Po doplnění skutečných klíčů lze spustit `scripts/live_acceptance.py`. Tento test provede skutečný AI požadavek, vytvoří nový model, uloží označený testovací projekt do Supabase, načte jeho parametry a stáhne privátní soubory. Testovací projekt ponechá v knihovně jako záznam ověření. Bez připojení skončí stavem `NOT_CONNECTED`, nikoliv falešným úspěchem.

## Spuštění na tomto počítači

1. Otevřete **START.cmd** ve složce aplikace.
2. Otevře se **http://127.0.0.1:5173/**.
3. Okno spouštěče ponechte otevřené. **Ctrl+C** zastaví pouze služby spuštěné tímto spouštěčem.

Z příkazové řádky ve složce aplikace:

    ..\.venv\Scripts\python.exe -X utf8 start.py

Pokud port 5173 používá jiný projekt, spusťte tento web na volném portu:

    ..\.venv\Scripts\python.exe -X utf8 start.py --port 5174

Náhled potom otevřete na http://127.0.0.1:5174/. Spouštěč cizí aplikaci nezastavuje.

Připravené Python prostředí je v sousední složce ../.venv/ a přenosný Blender 4.5.0 LTS v ../.tools/blender-4.5.0-windows-x64/. Archiv Blenderu byl ověřen oficiálním SHA-256 kontrolním součtem. Při přesunu aplikace vezměte tyto složky s sebou nebo proveďte instalaci níže.

## Doporučený postup živého dema

1. **Load demo project** → zkontrolujte halu **30 × 15 × 6 m**, **2 potrubí**, **Ø 600 mm**, výšku **4,5 m**.
2. **Generate concept**. Blender vytvoří a vyexportuje skutečnou scénu; v prohlížeči se načte GLB.
3. Tažení otáčí, kolečko přibližuje, pravé tlačítko posouvá. Vyzkoušejte **Overview / Front / Side / Inside / Detail**. **Present** rozšíří scénu a zapne plynulou kamerovou jízdu; **Pause tour** ji zastaví.
4. Přepněte **Illustrative airflow** mezi **Off / Lines / Animated**.
5. Do pole **Ask AI to modify the concept** vložte přesně:

   > Use three red ducts, move them one metre higher and point the nozzles 35 degrees downward.

6. Odešlete šipkou nebo klávesou Enter. Výsledkem jsou **3 červená potrubí ve výšce 5,5 m**, úhel **35°**, nová geometrie a souhrn **4 změn**.
7. **Undo** obnoví původní projekt i 3D model.
8. Druhá vstupní cesta: **New concept → Use example → Analyze request**. **Extracted** znamená hodnotu z textu, **Confirm** nepotvrzenou ukázkovou hodnotu, **Missing** nezadaný údaj. Po kontrole zvolte **Generate concept**.

Geometrie, ruční úpravy a omezený lokální parser fungují bez API klíče. Živé AI a Supabase vyžadují vlastní připojení. Před první generací je vpravo označený předem vygenerovaný **Demo preview**; změněné parametry se projeví až po generaci.

## Implementované funkce

- Validovaný strukturovaný projekt, ruční editor, označení chybějících požadavků.
- Deterministická extrakce parametrů a textové změny v Demo Mode.
- Parametrická kruhová i půlkruhová potrubí: počet, barva, průměr, délka, výška a rozteč.
- Průmyslová hala, konstrukce, zavěšení, stroje, regály a postavy pro měřítko.
- Mikroperforace, perforace, malé a velké trysky; směry a úhel distribuce.
- GLB viewer, kamery, otáčení, zoom, posun, animované ilustrativní proudění, pobytová zóna a rozměry.
- Skutečné přegenerování, přehled změn a jednoúrovňové undo.
- Export GLB a JSON projektu; ověřené uložení PNG aktuálního pohledu do složky projektu s náhledem a odkazem ke stažení.
- Ošetření neplatných dat, nepodporovaných příkazů, špatné cesty k Blenderu, pádu procesu, timeoutu, exportní chyby a nedostupného API.

## Požadavky a instalace na jiném počítači

- Windows 10/11; případně macOS/Linux s odpovídajícím Blenderem.
- Node.js 22.13+ (ověřeno s Node 24).
- Python 3.11+ (ověřeno s Python 3.12).
- Blender 4.5 LTS.
- Moderní prohlížeč s WebGL 2.

Příkazy spouštějte ze složky prihoda-ai-concept-studio:

    py -3 -m venv .venv
    .venv\Scripts\python.exe -m pip install -r backend/requirements.txt
    npm ci
    npm run build
    Copy-Item .env.example .env

Upravte .env a spusťte START.cmd. Na macOS/Linux použijte python3 -m venv .venv, .venv/bin/python -m pip install -r backend/requirements.txt a .venv/bin/python start.py.

### Blender ve Windows

Pokud není nalezen automaticky, nastavte skutečnou existující cestu v .env:

    BLENDER_PATH=C:/Program Files/Blender Foundation/Blender 4.5/blender.exe

Jde o příklad, existence této cesty se nepředpokládá. Detekce zkouší BLENDER_PATH, systémový PATH, sousední přenosnou instalaci .tools/blender-* a běžná instalační umístění. Nastavení `.env` se načítá za běhu.

### Samostatné spuštění pro vývoj

Terminál 1 – backend:

    $env:STUDIO_LOCAL_DEVELOPMENT='1'
    .venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

Na tomto připraveném počítači lze místo .venv použít ..\.venv. První řádek je pro PowerShell; v bash použijte `export STUDIO_LOCAL_DEVELOPMENT=1`. Vývojovou výjimku nepovolujte na veřejném serveru.

Terminál 2 – frontend s živými změnami:

    npm run dev

Produkční kontrola:

    npm run build
    npm run start

Frontend běží na 127.0.0.1:5173, backend na 127.0.0.1:8000. Oba poslouchají pouze lokálně. API dokumentace: http://127.0.0.1:8000/docs.

## Demo Mode a volitelný AI režim

Demo Mode neposílá požadavky do externího modelu a podporuje omezenou sadu frází:

- Use three red ducts
- Move the ducts one metre higher
- Move the ducts 1 m lower
- Increase diameter to 800 mm
- Point the nozzles 35° downward
- Make the hall 40 m long
- Use small nozzles
- Pouzij tri cervena potrubi a posun je o jeden metr vys

Česká diakritika a běžné české varianty jsou normalizovány. Nejde o obecné porozumění libovolné češtině. Nepodporovaný pokyn zobrazí chybu.

Pro OpenAI provider nastavte serverovou .env:

    OPENAI_API_KEY=
    OPENAI_MODEL=gpt-4.1-mini

Do OPENAI_API_KEY vložte svůj klíč nebo použijte dialog připojení. UI oznámí **AI MODE**. Server klíč nikdy nevrací do prohlížeče. Provider používá [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), Pydantic a povolené datové cesty. V AI Mode se text zákaznického požadavku a parametry odesílají OpenAI.

**Živá komunikace s placeným API nebyla bez klíče ověřena.** Odpovědi a chybové větve jsou ověřené lokálními testy. Pro workshop lze ponechat klíč prázdný.

## Architektura a výstupy

    app/                      React rozhraní a Three.js viewer
    backend/app/schemas.py    Pydantic model a validace patchů
    backend/app/ai.py         AIProvider a deterministický parser
    backend/app/services.py   detekce a řízené spouštění Blenderu
    blender/generate_scene.py jeden stabilní generátor
    projects/demo.json        výchozí demo
    projects/current_project.json poslední úspěšný nebo obnovený projekt
    output/<id>/              scene.blend, model.glb, manifest.json, project.json, blender.log
    output/demo/              demo včetně preview.png
    public/demo/              přibalený GLB/PNG fallback
    tests/                    funkční testy a audit skutečné scény
    .runtime/                 logy spouštěče

Vždy platí **text → validovaný JSON patch → validovaný projekt → pevný Blender generátor**. LLM nemění Python skripty ani nespouští příkazy. Úspěšné modely se cachují na disku i přes restart; změna generátoru zneplatní cache. Undo načte správný výstup a obnoví soubor aktuálního projektu.

Interaktivní generace vytváří GLB a .blend bez nákladného PNG renderu. Tlačítko PNG uloží aktuální pohled do output/exports/ a otevře náhled s odkazem ke stažení. Obrázek zůstane uložený i v prohlížeči, který nepodporuje automatické stahování. Pro skutečný Blender PNG render:

    & '..\.tools\blender-4.5.0-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python blender/generate_scene.py -- --project projects/demo.json --output output/manual-render --render

V aplikaci použijte **Render**, případně POST /api/generate?render=true s JSON projektem. PNG leží ve složce generace. Nové GLB má přibližně 2,7 MB. Eevee render má rozlišení 1600 × 1000; ověřený render na Intel UHD trval přibližně minutu. Živý viewer používá Three.js. Textilní normálová textura je součástí GLB. Statické vybavení je sloučeno podle materiálu pro snížení počtu vykreslovacích operací.

Zkontrolovaný finální výstup Studio 02 se třemi červenými potrubími je v **output/showcase/**: **scene.blend**, **model.glb**, **preview.png**, **manifest.json** a kopie vstupu **project.json**. Bílé demo nové verze je v **output/demo/**. Starší výstup v `output/final-render/` pochází z verze 1.

### Branding

Nezměněné [oficiální logo PŘÍHODA](https://www.prihoda.com/wp-content/themes/prihoda.com/assets/img/logo.svg) je v public/brand/prihoda-logo.svg. Zachovává původní barvy; červené akční prvky odpovídají zadání.

## Testy

    ..\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
    npm run build

tests/audit_scene.py se spouští uvnitř Blenderu nad skutečným .blend a kontroluje počet objektů, výšku, rozměr, materiál a orientaci trysek. Výsledky jsou v output/*audit.json a souhrn v VERIFICATION.md.

Po spuštění webu lze zopakovat kompletní test i kontrolu variant:

    ..\.venv\Scripts\python.exe -X utf8 -m tests.e2e
    ..\.venv\Scripts\python.exe -X utf8 -m tests.variants

## Řešení problémů

- **BLENDER NOT FOUND:** opravte BLENDER_PATH a restartujte backend. **Use demo preview** zpřístupní přibalené demo.
- **Backend offline:** zkontrolujte .runtime/backend.log a spusťte backend nebo START.cmd.
- **Generování / export selhal:** předchozí koncept zůstává zobrazen. Podrobnosti jsou v output/<id>/blender.log. Upravte parametry nebo opakujte generaci. Timeout geometrie je 150 s; volitelný CPU render PNG má limit 600 s.
- **AI nedostupné:** ověřte klíč, zvolený model a API kredit v Connections. Pro Demo Mode odstraňte hodnotu OPENAI_API_KEY ze souboru `.env` i případného prostředí procesu.
- **Port obsazený:** ukončete předchozí vlastní spouštěč pomocí Ctrl+C. Spouštěč neukončuje cizí procesy. Při změně portů upravte start.py, Vite proxy a CORS.
- **Model se nezobrazí:** ověřte WebGL 2 / hardwarovou akceleraci. Přibalené demo má PNG fallback; nový model lze vygenerovat znovu.
- **Menší hala:** zadejte také kratší potrubí a nižší instalaci. Aplikace odmítá kolizi se střechou, překrývání a potrubí mimo půdorys.
- **Chybějící tlak nebo požadovaná rychlost:** nedopočítávají se; potvrďte je před technickým návrhem.

## Omezení prototypu

Bez CFD, výrobní přesnosti trysek, uživatelské autentizace, BIM importu a PDF briefu. Server poslouchá jen na tomto počítači; zveřejnění víceuživatelské aplikace vyžaduje doplnění přihlášení a oddělení projektů. Výrobní hala, sklad a sportovní hala mají odlišné vybavení. Pobytová zóna 1,8 m a trajektorie jsou ilustrativní. Nevymýšlí se tlakové, rychlostní ani teplotní pole. Supabase odkazy na privátní soubory platí hodinu; pro nové odkazy projekt znovu otevřete. Přerušený cloudový zápis může zanechat nenavázané soubory, které se automaticky nemažou, aby opožděné potvrzení nemohlo zničit úspěšně uloženou verzi.
