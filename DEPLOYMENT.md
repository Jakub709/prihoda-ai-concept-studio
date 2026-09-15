# Nasazení na GitHub a Railway

Web, Python API a Blender běží v jednom Docker kontejneru. Supabase zůstává databází a úložištěm uložených projektů. Localhost lze dál spouštět přes `start.py`; úpravy ho nepřesouvají výhradně do cloudu.

## 1. GitHub

Nahrajte **obsah složky `prihoda-ai-concept-studio`**, nikoli nadřazenou složku Příhoda. Doporučený je soukromý repozitář `prihoda-ai-concept-studio`.

Přes GitHub Desktop: **File → Add local repository**, vyberte tuto složku a použijte **Publish repository**, s volbou **Keep this code private**. Případně se přihlaste přes `gh auth login` a publikujte připravený místní repozitář:

```sh
gh repo create prihoda-ai-concept-studio --private --source=. --remote=origin --push
```

`.gitignore` vynechává `.env`, klíče, místní aktuální projekt, výstupy, logy a závislosti. Do GitHubu nepatří ani jejich ručně přidané kopie. `.github/workflows/check.yml` provede sestavení, testy a skutečný Linux Docker / Blender CPU render. První kontrola bude trvat několik minut; před prezentací musí být zelená.

## 2. Railway

1. **New project → Deploy from GitHub repo**, povolte přístup k repozitáři a vyberte jej. Kořenem služby je kořen repozitáře s `Dockerfile`.
2. Railway použije `Dockerfile`. Start command ponechte prázdný: startuje `python serve.py`. Nenastavujte `npm start` ani `start.py`.
3. Připojte ke službě **Volume** s mount path **`/data`**. Uchovává rozpracované výstupy Blenderu a exporty i po restartu. SQL a uložené verze zůstávají v Supabase.
4. V **Variables** nastavte hodnoty z tabulky níže. Tajné hodnoty kopírujte z místního `.env` přímo do Railway, nikoli do GitHubu či chatu.
5. V **Networking → Generate domain** vytvořte HTTPS adresu. Target port nastavte na **8080**. Vraťte se do Variables a nastavte přesnou adresu jako `STUDIO_PUBLIC_ORIGIN`.
6. Healthcheck path nastavte na **`/api/health`**, timeout 120 sekund. Ponechte **1 repliku**, automatické uspávání vypněte. Aplikace používá jeden proces a jednu frontu Blenderu.
7. Pro první měření vyhraďte alespoň 2 vCPU a 4 GB RAM, pokud to tarif umožňuje. Jde o výchozí odhad, ne o ověřenou minimální konfiguraci. Zkontrolujte cenu, limit útraty a měření v Railway.
8. Proveďte deploy/redeploy po nastavení proměnných. Veřejná landing page se otevře každému; studio a soukromé soubory vyžadují přístupový kód.

| Proměnná | Hodnota |
| --- | --- |
| `PORT` | `8080` |
| `OPENAI_API_KEY` | Váš existující tajný klíč OpenAI |
| `OPENAI_MODEL` | Model z vašeho funkčního místního `.env` |
| `SUPABASE_URL` | `https://oxkbwixxsjxvxjuetwzc.supabase.co` |
| `SUPABASE_SECRET_KEY` | Existující serverový secret key; nikoli publishable key |
| `STUDIO_PUBLIC_ORIGIN` | Přesná `https://…up.railway.app` adresa bez cesty |
| `STUDIO_ACCESS_CODE` | Náhodný tajný kód o 16–256 znacích pro váš tým |
| `STUDIO_LOCAL_DEVELOPMENT` | `0` |
| `STUDIO_DATA_DIR` | `/data` |
| `BLENDER_PATH` | `/opt/blender/blender` |
| `BLENDER_RENDER_ENGINE` | `CYCLES` |

Poslední čtyři hodnoty jsou již nastavené v Docker image; nepřepisujte je hodnotami z místního Windows prostředí. Do žádné `VITE_*` proměnné nedávejte tajný klíč. SQL ve stávajícím Supabase projektu bylo již spuštěné, pro tento přesun není nová migrace potřeba. `SUPABASE_ACCESS_TOKEN` se na Railway nezadává.

Záměrně nepoužíváme starší `railway.toml`: Railway jej označuje jako zastaralý. Nasazení používá Dockerfile a výše uvedené nastavení služby. [Dockerfile](https://docs.railway.com/builds/dockerfiles), [Volumes](https://docs.railway.com/volumes), [stav config-as-code](https://docs.railway.com/config-as-code/reference).

## 3. Kontrola po nasazení

- V anonymním okně otevřete landing page a `/studio`: aplikace musí požadovat kód. `/api/status` a `/output/demo/scene.blend` bez přihlášení vracejí 401.
- Přihlaste se. Vytvořte vlastní koncept, změňte počet/barvu potrubí a vygenerujte PNG. Zkontrolujte 3D model i obrázek a dobu renderu.
- Uložte projekt do Supabase, obnovte stránku a otevřete jej přes Projects. Ověřte Původní zadání, PNG, historii a předchozí verzi.
- Restartujte službu a otevřete uložený projekt znovu. Rozpracovaný požadavek přerušený restartem spusťte znovu; fronta úloh je v paměti. Hotové soubory na Volume a uložené projekty v Supabase zůstávají.
- Nastavení klíčů je na veřejném webu pouze pro čtení. Spravujte je v Railway Variables. Při změně domény aktualizujte také `STUDIO_PUBLIC_ORIGIN`.

Před aktualizací nechte doběhnout rendery. Neukládaný stav otevřené stránky není záloha; hotový projekt vždy uložte do Supabase. Sledujte zaplnění Volume: automatické mazání uživatelských výstupů není zapnuté. Pro více současných týmů bude potřeba trvalá fronta a individuální účty; tato verze je pro společnou týmovou ukázku.

## Ověření Dockeru na počítači s Dockerem

```sh
docker build -t prihoda-studio .
docker run --rm -v "./scripts/smoke_container.py:/check.py:ro" prihoda-studio python /check.py
```

Smoke test používá jen demo, testovací kód a lokální CPU. Nevolá OpenAI ani Supabase a nepotřebuje tajné klíče. Testuje sestavený web, přihlášení, chráněné soubory a skutečný PNG/GLB render. Stejný test běží v GitHub Actions.
