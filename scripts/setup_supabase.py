"""Apply this app's additive migration to the Supabase project in .env.

Requires SUPABASE_ACCESS_TOKEN (Management API), distinct from the server key.
No credentials are printed. The alternative is the same SQL in SQL Editor.
"""
import sys
from pathlib import Path
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.config import setting, ROOT
from backend.app.storage import connection
from backend.app.network import tls_context

def main():
    try: url,_=connection()
    except RuntimeError as exc: raise SystemExit(str(exc))
    token=setting('SUPABASE_ACCESS_TOKEN')
    if not token:
        raise SystemExit('SUPABASE_ACCESS_TOKEN is missing. Run supabase/migrations/202609120001_prihoda_studio.sql in Supabase SQL Editor, or add a Management API token to the private .env file.')
    ref=url.split('//')[1].split('.')[0]
    sql=(ROOT/'supabase/migrations/202609120001_prihoda_studio.sql').read_text(encoding='utf-8')
    try:
        response=httpx.post(f'https://api.supabase.com/v1/projects/{ref}/database/query',
            headers={'Authorization':'Bearer '+token},json={'query':sql},timeout=60,verify=tls_context())
        response.raise_for_status()
    except httpx.HTTPError:
        raise SystemExit('Migration could not be verified. Check project permissions and the Management API token. No credentials were logged.')
    print('Supabase migration applied to '+ref+'. Open Connections and verify both services.')

if __name__=='__main__':main()
