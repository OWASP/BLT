"""
Tests for src/main.py – covers every routing branch of Default.on_fetch:
  - OPTIONS  → CORS preflight (204)
  - GET to known pages → 200 HTML
  - GET to unknown path → delegates to env.ASSETS or 404
  - POST / other methods → delegates to env.ASSETS or 404
  - FileNotFoundError → 404     (already covered in test_utils.py; duplicated here for clarity)
  - origin header propagation through the HTML response
"""

import sys
import os
import asyncio

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# ── Cloudflare workers mock ──────────────────────────────────────────────────
# Register a fake 'workers' module so that 'from workers import Response' in
# src/main.py and src/libs/utils.py does not raise an ImportError.
# We use setdefault so that if test_utils.py already registered the mock first
# (pytest discovers/imports modules in alphabetical order) we don't overwrite it.

if 'workers' not in sys.modules:
    _mock_workers = MagicMock()

    class _FakeResponse:
        def __init__(self, body, status=200, headers=None):
            raw = body or ''
            self.body = raw.encode('utf-8') if isinstance(raw, str) else raw
            self.status_code = status
            self.headers = headers or {}

    _mock_workers.Response = _FakeResponse
    _mock_workers.WorkerEntrypoint = type('WorkerEntrypoint', (), {})
    sys.modules['workers'] = _mock_workers

# ── Path setup ───────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import src.libs.utils as _utils_mod

if 'libs' not in sys.modules:
    sys.modules['libs'] = type(sys)('libs')
if 'libs.utils' not in sys.modules:
    sys.modules['libs.utils'] = _utils_mod

from src.main import Default  # noqa: E402  (after sys.modules setup)

# ── Helpers ──────────────────────────────────────────────────────────────────


def _req(method: str = 'GET', path: str = '/'):
    """Return a minimal fake request object."""
    r = MagicMock()
    r.method = method
    r.url = f'http://localhost{path}'
    r.headers = {}
    return r


def _env(has_assets: bool = False):
    """Return a fake env object, optionally with a fake ASSETS binding."""
    if has_assets:
        e = MagicMock(spec=['ASSETS'])
        e.ASSETS = AsyncMock()
        e.ASSETS.fetch = AsyncMock(
            return_value=sys.modules['workers'].Response('asset-body', 200))
    else:
        e = MagicMock(spec=[])
    return e


# ── OPTIONS (CORS preflight) ─────────────────────────────────────────────────


def test_options_returns_204():
    """OPTIONS to any path must return 204 No Content."""
    response = asyncio.run(Default().on_fetch(_req('OPTIONS', '/'), _env()))
    assert response.status_code == 204


def test_options_includes_preflight_headers():
    """OPTIONS response must include Access-Control-Allow-Methods and -Headers."""
    response = asyncio.run(Default().on_fetch(_req('OPTIONS', '/video-room'), _env()))
    assert response.status_code == 204
    assert 'GET, POST, OPTIONS' in response.headers.get('Access-Control-Allow-Methods', '')
    assert 'Content-Type' in response.headers.get('Access-Control-Allow-Headers', '')


def test_options_with_allowed_origin_returns_acao(monkeypatch):
    """OPTIONS with an allowlisted Origin must echo it in Access-Control-Allow-Origin."""
    monkeypatch.setenv('SAFE_CLOAK_ALLOWED_ORIGINS', 'https://example.com')
    req = _req('OPTIONS', '/')
    req.headers = {'Origin': 'https://example.com'}
    response = asyncio.run(Default().on_fetch(req, _env()))
    assert response.status_code == 204
    assert response.headers.get('Access-Control-Allow-Origin') == 'https://example.com'


def test_options_with_unknown_origin_omits_acao(monkeypatch):
    """OPTIONS with a non-allowlisted Origin must not set Access-Control-Allow-Origin."""
    monkeypatch.setenv('SAFE_CLOAK_ALLOWED_ORIGINS', 'https://allowed.example')
    req = _req('OPTIONS', '/')
    req.headers = {'Origin': 'https://unknown.example'}
    response = asyncio.run(Default().on_fetch(req, _env()))
    assert response.status_code == 204
    assert 'Access-Control-Allow-Origin' not in response.headers


# ── GET known pages ──────────────────────────────────────────────────────────


@pytest.mark.parametrize('path,expected_snippet', [
    ('/', b'BLT-SafeCloak'),
    ('/video-chat', b'SafeCloak'),
    ('/video-room', b'Video Room'),
    ('/notes', b'Notes'),
    ('/consent', b'Consent'),
])
def test_get_known_page_returns_200_html(path, expected_snippet):
    """GET to each registered page path must return 200 with HTML content."""
    response = asyncio.run(Default().on_fetch(_req('GET', path), _env()))
    assert response.status_code == 200
    assert response.headers.get('Content-Type', '').startswith('text/html')
    assert expected_snippet in response.body


def test_get_known_page_origin_propagated_to_cors_headers(monkeypatch):
    """Origin header on a GET page request should be echoed when allowlisted."""
    monkeypatch.setenv('SAFE_CLOAK_ALLOWED_ORIGINS', 'https://myapp.example')
    req = _req('GET', '/')
    req.headers = {'Origin': 'https://myapp.example'}
    response = asyncio.run(Default().on_fetch(req, _env()))
    assert response.status_code == 200
    assert response.headers.get('Access-Control-Allow-Origin') == 'https://myapp.example'


# ── GET unknown path – with / without ASSETS ────────────────────────────────


def test_get_unknown_path_with_assets_delegates_to_assets():
    """GET to an unrecognised path must forward the request to env.ASSETS.fetch."""
    req = _req('GET', '/static/some-file.js')
    env = _env(has_assets=True)
    asyncio.run(Default().on_fetch(req, env))
    env.ASSETS.fetch.assert_called_once_with(req)


def test_get_unknown_path_without_assets_returns_404():
    """GET to an unrecognised path without ASSETS binding must return 404."""
    response = asyncio.run(Default().on_fetch(_req('GET', '/unknown'), _env()))
    assert response.status_code == 404


# ── Non-GET / non-OPTIONS methods ────────────────────────────────────────────


def test_post_with_assets_delegates():
    """POST requests fall through to env.ASSETS (page routing is GET-only)."""
    req = _req('POST', '/notes')
    env = _env(has_assets=True)
    asyncio.run(Default().on_fetch(req, env))
    env.ASSETS.fetch.assert_called_once_with(req)


def test_post_without_assets_returns_404():
    """POST to a page path without ASSETS binding must return 404."""
    response = asyncio.run(Default().on_fetch(_req('POST', '/notes'), _env()))
    assert response.status_code == 404


def test_put_without_assets_returns_404():
    """PUT requests without ASSETS binding must return 404."""
    response = asyncio.run(Default().on_fetch(_req('PUT', '/'), _env()))
    assert response.status_code == 404


# ── Error handling ───────────────────────────────────────────────────────────


def test_missing_page_file_returns_404():
    """A missing page file triggers a FileNotFoundError and returns 404."""
    req = _req('GET', '/consent')
    env = _env()
    with patch('src.main.Path') as mock_path:
        inst = MagicMock()
        mock_path.return_value = inst
        inst.parent.__truediv__ = MagicMock(return_value=inst)
        inst.__truediv__ = MagicMock(return_value=inst)
        inst.read_text.side_effect = FileNotFoundError('consent.html missing')
        response = asyncio.run(Default().on_fetch(req, env))
    assert response.status_code == 404
    assert b'Not Found' in response.body


def test_unexpected_exception_returns_500():
    """An unexpected I/O error during page serving must return 500."""
    req = _req('GET', '/notes')
    env = _env()
    with patch('src.main.Path') as mock_path:
        inst = MagicMock()
        mock_path.return_value = inst
        inst.parent.__truediv__ = MagicMock(return_value=inst)
        inst.__truediv__ = MagicMock(return_value=inst)
        inst.read_text.side_effect = OSError('storage failure')
        response = asyncio.run(Default().on_fetch(req, env))
    assert response.status_code == 500
    assert b'Internal Server Error' in response.body


def test_cancelled_error_is_propagated():
    """asyncio.CancelledError must not be swallowed by the generic handler."""
    req = _req('GET', '/')
    env = _env()
    with patch('src.main.Path') as mock_path:
        inst = MagicMock()
        mock_path.return_value = inst
        inst.parent.__truediv__ = MagicMock(return_value=inst)
        inst.__truediv__ = MagicMock(return_value=inst)
        inst.read_text.side_effect = asyncio.CancelledError()
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(Default().on_fetch(req, env))
