"""Routing tests for blt-dash/src/index.py

Tests:
  - /dash and /dash/ return 302 redirecting to root (/)
  - /dash/<subpath> rewrites to /<subpath> and fetches from ASSETS
  - Static asset requests (/) are passed through to env.ASSETS
  - OPTIONS preflight returns CORS headers
  - Missing env.ASSETS binding returns 500 configuration error
"""

import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent


# ── Fakes for Cloudflare Workers JS Runtime ──────────────────────────────────

class FakeHeaders:
    def __init__(self, init=None):
        self._h = {}
        if isinstance(init, FakeHeaders):
            self._h.update(init._h)
        elif isinstance(init, dict):
            for k, v in init.items():
                self.set(k, v)

    def set(self, key, value):
        self._h[key.lower()] = value

    def get(self, key, default=None):
        return self._h.get(key.lower(), default)

    def items(self):
        return self._h.items()


class FakeResponse:
    def __init__(self, body=None, status=200, headers=None):
        self.body = body
        self.status = status
        self.headers = headers if isinstance(headers, FakeHeaders) else FakeHeaders(headers or {})

    @classmethod
    def new(cls, body=None, init=None):
        init = init or {}
        return cls(body, status=init.get('status', 200), headers=init.get('headers'))

    @classmethod
    def redirect(cls, url, status=302):
        headers = FakeHeaders({'Location': str(url)})
        return cls(None, status=status, headers=headers)


class FakeURL:
    def __init__(self, url, base=None):
        if base:
            base_parts = urlsplit(str(base))
            url = f"{base_parts.scheme}://{base_parts.netloc}{url}"
        self._url = str(url)
        parts = urlsplit(self._url)
        self.scheme = parts.scheme
        self.netloc = parts.netloc
        self._pathname = parts.path or '/'

    @property
    def pathname(self):
        return self._pathname

    @pathname.setter
    def pathname(self, val):
        self._pathname = val
        self._url = f"{self.scheme}://{self.netloc}{val}"

    @classmethod
    def new(cls, url, base=None):
        return cls(url, base)

    def __str__(self):
        return self._url


class FakeRequest:
    def __init__(self, url, init=None, method='GET', headers=None):
        if init and hasattr(init, 'method'):
            self.url = str(url)
            self.method = init.method
            self.headers = init.headers
        else:
            self.url = str(url)
            self.method = method
            self.headers = FakeHeaders(headers or {})

    @classmethod
    def new(cls, url, init=None):
        return cls(url, init)


class FakeAssets:
    """Mock Cloudflare ASSETS binding."""
    def __init__(self, paths=('/', '/index.html', '/logo.svg')):
        self.paths = set(paths)
        self.calls = []

    async def fetch(self, request):
        self.calls.append(request)
        path = urlsplit(request.url).path
        if path in self.paths:
            return FakeResponse('<html>content</html>', status=200)
        return FakeResponse('Not Found', status=404)


# ── Load Worker ──────────────────────────────────────────────────────────────

def load_worker():
    sys.modules['js'] = types.SimpleNamespace(
        Request=FakeRequest,
        Response=FakeResponse,
        URL=FakeURL,
        Headers=FakeHeaders,
    )
    spec = importlib.util.spec_from_file_location('blt_dash_index', PROJECT / 'src' / 'index.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ── Tests ────────────────────────────────────────────────────────────────────

class TestDashRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worker = load_worker()

    def run_async(self, coro):
        return asyncio.run(coro)

    def test_redirect_dash_exact(self):
        """GET /dash returns 302 redirect to root (/)."""
        req = FakeRequest('https://dash.owaspblt.org/dash')
        env = types.SimpleNamespace(ASSETS=FakeAssets())
        res = self.run_async(self.worker.on_fetch(req, env))

        self.assertEqual(res.status, 302)
        location = res.headers.get('Location')
        self.assertTrue(location.endswith('/'), f"Expected Location ending in '/', got {location}")

    def test_redirect_dash_slash(self):
        """GET /dash/ returns 302 redirect to root (/)."""
        req = FakeRequest('https://dash.owaspblt.org/dash/')
        env = types.SimpleNamespace(ASSETS=FakeAssets())
        res = self.run_async(self.worker.on_fetch(req, env))

        self.assertEqual(res.status, 302)
        location = res.headers.get('Location')
        self.assertTrue(location.endswith('/'), f"Expected Location ending in '/', got {location}")

    def test_subpath_rewrite_to_assets(self):
        """GET /dash/logo.svg rewrites path to /logo.svg and passes to ASSETS."""
        assets = FakeAssets()
        req = FakeRequest('https://dash.owaspblt.org/dash/logo.svg')
        env = types.SimpleNamespace(ASSETS=assets)
        res = self.run_async(self.worker.on_fetch(req, env))

        self.assertEqual(res.status, 200)
        self.assertEqual(len(assets.calls), 1)
        # Verify the URL passed to ASSETS was stripped of /dash prefix:
        self.assertEqual(assets.calls[0].url, 'https://dash.owaspblt.org/logo.svg')

    def test_root_asset_fetch(self):
        """GET / passes through untouched to ASSETS."""
        assets = FakeAssets()
        req = FakeRequest('https://dash.owaspblt.org/')
        env = types.SimpleNamespace(ASSETS=assets)
        res = self.run_async(self.worker.on_fetch(req, env))

        self.assertEqual(res.status, 200)
        self.assertEqual(assets.calls[0].url, 'https://dash.owaspblt.org/')

    def test_options_cors_preflight(self):
        """OPTIONS preflight returns 200 with CORS headers."""
        req = FakeRequest('https://dash.owaspblt.org/', method='OPTIONS')
        env = types.SimpleNamespace(ASSETS=FakeAssets())
        res = self.run_async(self.worker.on_fetch(req, env))

        self.assertEqual(res.status, 200)
        self.assertEqual(res.headers.get('Access-Control-Allow-Origin'), '*')

    def test_missing_assets_binding_returns_500(self):
        """When ASSETS binding is missing, worker returns 500 misconfiguration error."""
        req = FakeRequest('https://dash.owaspblt.org/')
        env = types.SimpleNamespace()  # No ASSETS binding
        res = self.run_async(self.worker.on_fetch(req, env))

        self.assertEqual(res.status, 500)
        self.assertIn('ASSETS binding', res.body)


if __name__ == '__main__':
    unittest.main()
