"""Private, reloadable settings. Secret values never leave the backend."""
import os
from pathlib import Path
from threading import Lock
from dotenv import dotenv_values, set_key

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / '.env'
LOCK = Lock()

def setting(name, default=''):
    # Explicit server variables (including empty values) override local settings.
    if name in os.environ:
        return os.environ[name]
    return dotenv_values(ENV).get(name) or default

def data_root(default=ROOT):
    return Path(setting('STUDIO_DATA_DIR', str(default))).expanduser().resolve()

def configure(values):
    allowed = {'OPENAI_API_KEY', 'OPENAI_MODEL', 'SUPABASE_URL', 'SUPABASE_SECRET_KEY'}
    with LOCK:
        ENV.touch(exist_ok=True)
        for name, value in values.items():
            if name in allowed and value and value.strip():
                set_key(str(ENV), name, value.strip())

def public_settings():
    return {
        'openai_configured': bool(setting('OPENAI_API_KEY')),
        'openai_model': setting('OPENAI_MODEL', 'gpt-4.1-mini'),
        'supabase_configured': bool(setting('SUPABASE_URL') and (setting('SUPABASE_SECRET_KEY') or setting('SUPABASE_SERVICE_ROLE_KEY'))),
        'supabase_url': setting('SUPABASE_URL'),
    }
