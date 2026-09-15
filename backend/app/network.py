"""Use the OS trust store, including managed Windows certificates."""
from functools import lru_cache
import ssl

@lru_cache(maxsize=1)
def tls_context():
    # Retain hostname and certificate-chain verification. HTTPX's standalone
    # certifi bundle does not include this computer's managed trust roots.
    return ssl.create_default_context()
