"""Closed-team access. Public servers fail closed until configured.

Local bypass is explicitly enabled by the loopback-only development launcher.
Changing the access code invalidates all signed sessions. No client-side secrets.
"""
import hashlib
import hmac
import ipaddress
import os
import secrets
import time
from collections import OrderedDict
from threading import Lock
from urllib.parse import urlsplit
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from .config import setting

router = APIRouter(prefix='/api/auth')
COOKIE = 'prihoda_studio_session'
TTL = 8 * 60 * 60
ATTEMPTS = OrderedDict()
ATTEMPT_LOCK = Lock()

def public_origin():
    return setting('STUDIO_PUBLIC_ORIGIN').strip().rstrip('/')

def configured():
    try:
        origin = urlsplit(public_origin())
        origin.port
    except ValueError:
        return False
    return (16 <= len(setting('STUDIO_ACCESS_CODE')) <= 256 and origin.scheme == 'https'
            and bool(origin.hostname) and not origin.username and not origin.password
            and not origin.path and not origin.query and not origin.fragment)

def is_loopback(value):
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return value == 'localhost'

def local_development(request: Request):
    # A configured public origin or access code always disables the bypass.
    # Forwarded requests never qualify, even when a proxy rewrites Host.
    return (os.environ.get('STUDIO_LOCAL_DEVELOPMENT', setting('STUDIO_LOCAL_DEVELOPMENT')) == '1'
            and not public_origin() and not setting('STUDIO_ACCESS_CODE')
            and request.client is not None and is_loopback(request.client.host)
            and is_loopback(request.url.hostname or '')
            and not any(name in request.headers for name in ('forwarded', 'x-forwarded-for', 'x-forwarded-host', 'x-forwarded-proto')))

def trusted_origin(request: Request):
    origin = request.headers.get('origin')
    if not origin:
        return request.headers.get('sec-fetch-site') != 'cross-site'
    if configured() and origin == public_origin():
        return True
    return local_development(request) and origin in (
        str(request.base_url).rstrip('/'),
        'http://localhost:5173', 'http://127.0.0.1:5173',
        'http://localhost:8000', 'http://127.0.0.1:8000')

def signature(payload):
    return hmac.new(setting('STUDIO_ACCESS_CODE').encode(),
                    ('prihoda-session-v1:' + payload).encode(), hashlib.sha256).hexdigest()

def create_session():
    payload = str(int(time.time()) + TTL) + '.' + secrets.token_hex(24)
    return payload + '.' + signature(payload)

def authenticated(request: Request):
    if local_development(request):
        return True
    if not configured():
        return False
    token = request.cookies.get(COOKIE, '')
    if len(token) > 150:
        return False
    try:
        expires, nonce, signed = token.split('.')
        payload = expires + '.' + nonce
        return (len(nonce) == 48 and time.time() < int(expires) <= time.time() + TTL
                and hmac.compare_digest(signature(payload), signed))
    except (ValueError, TypeError):
        return False

async def protect_studio(request: Request, call_next):
    path = request.url.path
    private = path.startswith(('/api/', '/output/')) or path in ('/api', '/output', '/docs', '/redoc', '/openapi.json', '/docs/oauth2-redirect')
    public = path in ('/api/health', '/api/auth/session', '/api/auth/login', '/api/auth/logout')
    if private and request.method not in ('GET', 'HEAD', 'OPTIONS') and not trusted_origin(request):
        return JSONResponse(status_code=403, content={'detail': 'Tento požadavek není z povolené adresy studia.'}, headers={'Cache-Control': 'no-store'})
    if private and not public and not authenticated(request):
        return JSONResponse(status_code=401, content={'detail': 'Pro vstup do studia se přihlaste.'}, headers={'Cache-Control': 'no-store'})
    if path in ('/api/connections', '/api/connections/test') and request.method == 'POST' and not local_development(request):
        return JSONResponse(status_code=403, content={'detail': 'Připojení služeb spravuje správce přímo na serveru.'}, headers={'Cache-Control': 'no-store'})
    response = await call_next(request)
    if private:
        # Protect user models from being served from shared browser/proxy caches.
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Vary'] = ', '.join(filter(None, (response.headers.get('Vary'), 'Cookie')))
    return response

@router.get('/session')
def session(request: Request):
    return {'authenticated': authenticated(request), 'configured': bool(configured()),
            'local': bool(local_development(request))}

class LoginInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    code: str = Field(min_length=1, max_length=256)

@router.post('/login')
def login(data: LoginInput, request: Request, response: Response):
    if not configured():
        raise HTTPException(503, 'Přístup do studia ještě není aktivovaný. Obraťte se na správce.')
    # Use the actual peer address, never an untrusted forwarded header. Behind
    # a proxy this deliberately provides a shared limit for this small team.
    peer = request.client.host if request.client else 'unknown'
    now = time.monotonic()
    with ATTEMPT_LOCK:
        attempts, until = ATTEMPTS.get(peer, (0, now + 15 * 60))
        if until <= now:
            attempts, until = 0, now + 15 * 60
        if attempts >= 5:
            raise HTTPException(429, 'Příliš mnoho pokusů. Zkuste to znovu za 15 minut.', headers={'Retry-After': str(max(1, int(until - now)))})
        ATTEMPTS[peer] = (attempts + 1, until)
        ATTEMPTS.move_to_end(peer)
        while len(ATTEMPTS) > 4096:
            ATTEMPTS.popitem(last=False)
    if not hmac.compare_digest(data.code.encode(), setting('STUDIO_ACCESS_CODE').encode()):
        raise HTTPException(401, 'Přístupový kód není správný. Zkuste to znovu.')
    with ATTEMPT_LOCK:
        ATTEMPTS.pop(peer, None)
    response.set_cookie(COOKIE, create_session(), max_age=TTL, httponly=True, secure=True, samesite='strict', path='/')
    return {'authenticated': True, 'local': False, 'configured': True}

@router.post('/logout')
def logout(response: Response):
    response.delete_cookie(COOKIE, path='/', httponly=True, secure=True, samesite='strict')
    return {'authenticated': False}
