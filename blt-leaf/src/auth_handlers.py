"""HTTP handlers for GitHub OAuth authentication."""

import json
from datetime import datetime, timezone
from urllib.parse import urlencode

from js import Headers, Object, Response, URL, fetch
from pyodide.ffi import to_js

from auth import (
    build_absolute_url,
    build_session_cookie,
    build_state_cookie,
    clear_session_cookie,
    clear_state_cookie,
    encrypt_session,
    generate_oauth_state,
    get_app_root_path,
    get_oauth_scope,
    get_oauth_session,
    get_request_prefix,
    is_oauth_configured,
    resolve_github_token,
    validate_oauth_state,
)


def _json_response(payload: dict, status: int = 200):
    return Response.new(
        json.dumps(payload),
        {
            'status': status,
            'headers': {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-store',
            },
        },
    )


def _redirect_response(location: str, cookies=None):
    # Some Python Worker runtimes may not consistently preserve 302/Location.
    # Return an HTML auto-redirect fallback so browser navigation still works.
    escaped_location = location.replace('&', '&amp;').replace('"', '&quot;')
    html = (
        '<!doctype html><html><head>'
        f'<meta http-equiv="refresh" content="0;url={escaped_location}">'
        f'<script>window.location.replace({json.dumps(location)});</script>'
        '</head><body>'
        f'<a href="{escaped_location}">Continue</a>'
        '</body></html>'
    )
    response = Response.new(html)
    response.headers.set('Content-Type', 'text/html; charset=UTF-8')
    response.headers.set('Cache-Control', 'no-store')
    response.headers.set('Location', location)

    for cookie in cookies or []:
        response.headers.append('Set-Cookie', cookie)

    return response


def _build_callback_url(request) -> str:
    prefix = get_request_prefix(request)
    callback_path = f'{prefix}/api/auth/callback' if prefix else '/api/auth/callback'
    return build_absolute_url(request, callback_path)


async def _exchange_code_for_token(code: str, request, env):
    client_id = (getattr(env, 'GITHUB_OAUTH_CLIENT_ID', '') or '').strip()
    client_secret = (getattr(env, 'GITHUB_OAUTH_CLIENT_SECRET', '') or '').strip()

    body = urlencode(
        {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'redirect_uri': _build_callback_url(request),
        }
    )

    headers = Headers.new(
        to_js(
            {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'BLT-Leaf/1.0',
            },
            dict_converter=Object.fromEntries,
        )
    )

    options = to_js(
        {
            'method': 'POST',
            'headers': headers,
            'body': body,
        },
        dict_converter=Object.fromEntries,
    )

    response = await fetch('https://github.com/login/oauth/access_token', options)

    if not response.ok:
        raise Exception(f"GitHub OAuth token exchange failed: status={response.status}")

    payload = (await response.json()).to_py()

    access_token = payload.get('access_token')
    if not access_token:
        raise Exception('GitHub OAuth token exchange returned no access_token')

    return payload


async def _fetch_github_user(access_token: str):
    headers = Headers.new(
        to_js(
            {
                'Accept': 'application/vnd.github+json',
                'Authorization': f'Bearer {access_token}',
                'X-GitHub-Api-Version': '2022-11-28',
                'User-Agent': 'BLT-Leaf/1.0',
            },
            dict_converter=Object.fromEntries,
        )
    )

    response = await fetch(
        'https://api.github.com/user',
        to_js({'method': 'GET', 'headers': headers}, dict_converter=Object.fromEntries),
    )

    if not response.ok:
        raise Exception(f"GitHub user fetch failed: status={response.status}")

    return (await response.json()).to_py()


async def handle_auth_login(request, env):
    if not is_oauth_configured(env):
        return _json_response(
            {
                'error': 'GitHub OAuth is not configured. Set GITHUB_OAUTH_CLIENT_ID, GITHUB_OAUTH_CLIENT_SECRET, and ENCRYPTION_KEY.',
                'oauth_enabled': False,
            },
            status=503,
        )

    client_id = (getattr(env, 'GITHUB_OAUTH_CLIENT_ID', '') or '').strip()
    state = generate_oauth_state()

    authorize_query = urlencode(
        {
            'client_id': client_id,
            'scope': get_oauth_scope(env),
            'state': state,
            'redirect_uri': _build_callback_url(request),
        }
    )
    authorize_url = f'https://github.com/login/oauth/authorize?{authorize_query}'

    return _redirect_response(authorize_url, cookies=[build_state_cookie(state)])


async def handle_auth_callback(request, env):
    root_path = get_app_root_path(request)
    url = URL.new(request.url)

    oauth_error = url.searchParams.get('error')
    if oauth_error:
        return _redirect_response(
            f'{root_path}?auth=error',
            cookies=[clear_state_cookie()],
        )

    code = url.searchParams.get('code')
    state = url.searchParams.get('state')

    if not code:
        return _redirect_response(
            f'{root_path}?auth=error',
            cookies=[clear_state_cookie()],
        )

    if not validate_oauth_state(request, state):
        return _redirect_response(
            f'{root_path}?auth=error',
            cookies=[clear_state_cookie()],
        )

    if not is_oauth_configured(env):
        return _redirect_response(
            f'{root_path}?auth=error',
            cookies=[clear_state_cookie()],
        )

    try:
        token_payload = await _exchange_code_for_token(code, request, env)
        access_token = token_payload.get('access_token')
        github_user = await _fetch_github_user(access_token)

        issued_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        session_payload = {
            'access_token': access_token,
            'scope': token_payload.get('scope', ''),
            'token_type': token_payload.get('token_type', 'bearer'),
            'issued_at': issued_at,
            'user': {
                'login': github_user.get('login'),
                'avatar_url': github_user.get('avatar_url'),
                'name': github_user.get('name'),
            },
        }

        encrypted_session = await encrypt_session(session_payload, env)
        return _redirect_response(
            f'{root_path}?auth=success',
            cookies=[
                build_session_cookie(encrypted_session),
                clear_state_cookie(),
            ],
        )
    except Exception as exc:
        response = _redirect_response(f'{root_path}?auth=error')
        response.headers.append('Set-Cookie', clear_state_cookie())
        print(f'GitHub OAuth callback error: {type(exc).__name__}: {str(exc)}')
        return response


async def handle_auth_user(request, env):
    oauth_enabled = is_oauth_configured(env)
    resolved = await resolve_github_token(request, env)

    authenticated = resolved.get('oauth_authenticated', False)
    invalid_cookie = resolved.get('invalid_oauth_cookie', False)
    token_source = resolved.get('token_source', 'unauthenticated')
    user_payload = resolved.get('user') or None

    response = _json_response(
        {
            'authenticated': authenticated,
            'oauth_enabled': oauth_enabled,
            'token_source': token_source,
            'user': user_payload,
            'session_cookie_present': bool(request.headers.get('cookie') and 'blt_oauth_session=' in (request.headers.get('cookie') or '')),
            'session_cookie_valid': authenticated,
            'auth_reason': (
                'authenticated' if authenticated else
                'invalid_session_cookie' if invalid_cookie else
                'missing_session_cookie' if oauth_enabled else
                'oauth_not_configured'
            ),
        }
    )
    response.headers.set('Vary', 'Cookie')

    if invalid_cookie:
        response.headers.append('Set-Cookie', clear_session_cookie())

    return response


async def handle_auth_logout(request, env):
    response = _json_response({'success': True, 'authenticated': False})
    response.headers.append('Set-Cookie', clear_session_cookie())
    response.headers.append('Set-Cookie', clear_state_cookie())
    return response
