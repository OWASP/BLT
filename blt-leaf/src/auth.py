"""Authentication and token resolution helpers for GitHub OAuth."""

import base64
import hmac
import json
import os
import secrets
from typing import Dict, Optional, Tuple
from urllib.parse import unquote

from js import URL, Uint8Array, crypto, Object
from pyodide.ffi import to_js

SESSION_COOKIE_NAME = 'blt_oauth_session'
STATE_COOKIE_NAME = 'blt_oauth_state'
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
STATE_MAX_AGE = 60 * 10  # 10 minutes

_cached_key_bytes = None
_cached_crypto_key = None


def _bytes_to_uint8array(data: bytes):
    arr = Uint8Array.new(len(data))
    for i, value in enumerate(data):
        arr[i] = value
    return arr


def _uint8array_to_bytes(arr) -> bytes:
    py_data = arr.to_py()
    try:
        return bytes(py_data)
    except Exception:
        return bytes(list(py_data))


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')


def _b64url_decode(data: str) -> bytes:
    padding = '=' * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _decode_encryption_key(env) -> bytes:
    key_b64 = (getattr(env, 'ENCRYPTION_KEY', '') or '').strip()
    if not key_b64:
        raise ValueError('ENCRYPTION_KEY is required for OAuth session encryption')

    try:
        key_bytes = base64.b64decode(key_b64)
    except Exception as exc:
        raise ValueError('ENCRYPTION_KEY must be valid base64') from exc

    if len(key_bytes) != 32:
        raise ValueError('ENCRYPTION_KEY must decode to exactly 32 bytes')

    return key_bytes


async def _get_crypto_key(env):
    global _cached_key_bytes, _cached_crypto_key

    key_bytes = _decode_encryption_key(env)
    if _cached_crypto_key is not None and _cached_key_bytes == key_bytes:
        return _cached_crypto_key

    key = await crypto.subtle.importKey(
        'raw',
        _bytes_to_uint8array(key_bytes),
        to_js({'name': 'AES-GCM'}, dict_converter=Object.fromEntries),
        False,
        to_js(['encrypt', 'decrypt'])
    )

    _cached_key_bytes = key_bytes
    _cached_crypto_key = key
    return key


def parse_cookies(request) -> Dict[str, str]:
    header = request.headers.get('cookie') or ''
    cookies = {}

    for part in header.split(';'):
        if '=' not in part:
            continue
        name, value = part.split('=', 1)
        cookie_name = name.strip()
        cookie_value = value.strip()
        if len(cookie_value) >= 2 and cookie_value[0] == '"' and cookie_value[-1] == '"':
            cookie_value = cookie_value[1:-1]
        cookies[cookie_name] = unquote(cookie_value)

    return cookies


def get_cookie_value(request, name: str) -> Optional[str]:
    return parse_cookies(request).get(name)


def build_set_cookie(name: str, value: str, max_age: int, path: str = '/', http_only: bool = True, secure: bool = True, same_site: str = 'Lax') -> str:
    parts = [
        f'{name}={value}',
        f'Path={path}',
        f'Max-Age={int(max_age)}',
        f'SameSite={same_site}',
    ]

    if secure:
        parts.append('Secure')
    if http_only:
        parts.append('HttpOnly')

    return '; '.join(parts)


def build_clear_cookie(name: str, path: str = '/') -> str:
    return '; '.join([
        f'{name}=',
        f'Path={path}',
        'Max-Age=0',
        'Expires=Thu, 01 Jan 1970 00:00:00 GMT',
        'SameSite=Lax',
        'Secure',
        'HttpOnly',
    ])


def build_state_cookie(state: str) -> str:
    return build_set_cookie(STATE_COOKIE_NAME, state, STATE_MAX_AGE)


def build_session_cookie(encrypted_session: str) -> str:
    return build_set_cookie(SESSION_COOKIE_NAME, encrypted_session, SESSION_MAX_AGE)


def clear_state_cookie() -> str:
    return build_clear_cookie(STATE_COOKIE_NAME)


def clear_session_cookie() -> str:
    return build_clear_cookie(SESSION_COOKIE_NAME)


def generate_oauth_state() -> str:
    return secrets.token_urlsafe(32)


def get_request_prefix(request) -> str:
    pathname = URL.new(request.url).pathname
    if pathname == '/leaf' or pathname.startswith('/leaf/'):
        return '/leaf'
    return ''


def get_app_root_path(request) -> str:
    prefix = get_request_prefix(request)
    return f'{prefix}/' if prefix else '/'


def build_absolute_url(request, path: str) -> str:
    url = URL.new(request.url)
    normalized = path if path.startswith('/') else f'/{path}'
    return f'{url.origin}{normalized}'


def is_oauth_configured(env) -> bool:
    client_id = (getattr(env, 'GITHUB_OAUTH_CLIENT_ID', '') or '').strip()
    client_secret = (getattr(env, 'GITHUB_OAUTH_CLIENT_SECRET', '') or '').strip()
    if not (client_id and client_secret):
        return False

    try:
        _decode_encryption_key(env)
        return True
    except Exception:
        return False


def get_oauth_scope(env) -> str:
    scope = (getattr(env, 'GITHUB_OAUTH_SCOPE', '') or '').strip()
    return scope or 'repo read:user'


async def encrypt_session(payload: dict, env) -> str:
    key = await _get_crypto_key(env)
    iv = os.urandom(12)
    plaintext = json.dumps(payload, separators=(',', ':')).encode('utf-8')

    params = to_js(
        {'name': 'AES-GCM', 'iv': _bytes_to_uint8array(iv)},
        dict_converter=Object.fromEntries
    )

    encrypted_buffer = await crypto.subtle.encrypt(
        params,
        key,
        _bytes_to_uint8array(plaintext)
    )
    encrypted_bytes = _uint8array_to_bytes(Uint8Array.new(encrypted_buffer))

    return f"v1.{_b64url_encode(iv)}.{_b64url_encode(encrypted_bytes)}"


async def decrypt_session(encoded_payload: str, env) -> dict:
    if not encoded_payload:
        raise ValueError('Missing encrypted payload')

    parts = encoded_payload.split('.')
    if len(parts) != 3 or parts[0] != 'v1':
        raise ValueError('Unsupported session payload format')

    iv = _b64url_decode(parts[1])
    ciphertext = _b64url_decode(parts[2])

    key = await _get_crypto_key(env)
    params = to_js(
        {'name': 'AES-GCM', 'iv': _bytes_to_uint8array(iv)},
        dict_converter=Object.fromEntries
    )

    decrypted_buffer = await crypto.subtle.decrypt(
        params,
        key,
        _bytes_to_uint8array(ciphertext)
    )

    decrypted_bytes = _uint8array_to_bytes(Uint8Array.new(decrypted_buffer))
    return json.loads(decrypted_bytes.decode('utf-8'))


async def get_oauth_session(request, env) -> Tuple[Optional[dict], bool]:
    """Return (session_payload, invalid_cookie)."""
    cookie_value = get_cookie_value(request, SESSION_COOKIE_NAME)
    if not cookie_value:
        return (None, False)

    try:
        session_payload = await decrypt_session(cookie_value, env)
    except Exception:
        return (None, True)

    if not isinstance(session_payload, dict):
        return (None, True)

    if not session_payload.get('access_token'):
        return (None, True)

    return (session_payload, False)


def validate_oauth_state(request, state_from_query: Optional[str]) -> bool:
    cookie_state = get_cookie_value(request, STATE_COOKIE_NAME)
    if not cookie_state or not state_from_query:
        return False
    return hmac.compare_digest(str(cookie_state), str(state_from_query))


async def resolve_github_token(request, env) -> dict:
    """Resolve token source priority: OAuth cookie -> header token -> shared token -> none."""
    session_payload, invalid_cookie = await get_oauth_session(request, env)

    if session_payload and session_payload.get('access_token'):
        user_info = session_payload.get('user') or {}
        return {
            'token': session_payload['access_token'],
            'token_source': 'user_oauth',
            'oauth_authenticated': True,
            'token_configured': True,
            'user': {
                'login': user_info.get('login'),
                'avatar_url': user_info.get('avatar_url'),
                'name': user_info.get('name'),
            },
            'invalid_oauth_cookie': invalid_cookie,
        }

    header_token = (request.headers.get('x-github-token') or '').strip()
    if header_token:
        return {
            'token': header_token,
            'token_source': 'header_token',
            'oauth_authenticated': False,
            'token_configured': True,
            'user': None,
            'invalid_oauth_cookie': invalid_cookie,
        }

    shared_token = (getattr(env, 'GITHUB_TOKEN', '') or '').strip()
    if shared_token:
        return {
            'token': shared_token,
            'token_source': 'shared_token',
            'oauth_authenticated': False,
            'token_configured': True,
            'user': None,
            'invalid_oauth_cookie': invalid_cookie,
        }

    return {
        'token': None,
        'token_source': 'unauthenticated',
        'oauth_authenticated': False,
        'token_configured': False,
        'user': None,
        'invalid_oauth_cookie': invalid_cookie,
    }
