"""Routing tests for workers/main.py: legacy redirects, own routes and the 404 page.

The Worker imports `js` and `workers`, which only exist inside the Cloudflare Python runtime,
so small fakes stand in for them here. Run with: python3 -m unittest discover -s tests
"""
import asyncio
import importlib.util
import json
import re
import sys
import types
import unittest
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent


# ---- fakes for the Workers runtime -------------------------------------------------------

class FakeHeaders:
    def __init__(self, init=None):
        self._h = {}
        if isinstance(init, FakeHeaders):
            self._h.update(init._h)
        elif isinstance(init, dict):
            for k, v in init.items():
                self.set(k, v)

    @classmethod
    def new(cls, init=None):
        return cls(init)

    def set(self, key, value):
        self._h[key.lower()] = value

    def get(self, key, default=None):
        return self._h.get(key.lower(), default)


class FakeResponse:
    def __init__(self, body=None, status=200, headers=None):
        self.body = body
        self.status = status
        self.headers = headers if headers is not None else FakeHeaders()

    @classmethod
    def new(cls, body=None, status=200, headers=None):
        return cls(body, status=status, headers=headers)


class FakeURL:
    def __init__(self, url):
        parts = urlsplit(url)
        self.pathname = parts.path or '/'
        self.search = f'?{parts.query}' if parts.query else ''
        self._url = url

    @classmethod
    def new(cls, url):
        return cls(url)

    def __str__(self):
        return self._url


class FakeRequest:
    def __init__(self, url, method='GET', headers=None, body=None):
        self.url = url
        self.method = method
        self.headers = FakeHeaders(headers or {})
        self._body = body

    async def json(self):
        return json.loads(self._body)


class FakeAssets:
    """Serves a fixed set of paths; anything else is a 404, like the real binding."""

    def __init__(self, paths=('/', '/pages/about')):
        self.paths = set(paths)
        self.calls = []

    async def fetch(self, request):
        # The real runtime crashes (Pyodide fatal error, Cloudflare 1101) when handed a
        # Request built from a Python dict, so insist on a request object.
        assert not isinstance(request, dict), 'ASSETS.fetch must get a Request, not a dict'
        self.calls.append(request)
        path = urlsplit(request.url).path
        if path in self.paths:
            return FakeResponse('<html>asset</html>', status=200, headers=FakeHeaders({'Content-Type': 'text/html'}))
        return FakeResponse(None, status=404)


class FakeEntrypoint:
    def __init__(self, env=None):
        self.env = env


def load_worker():
    sys.modules['js'] = types.SimpleNamespace(Response=FakeResponse, Headers=FakeHeaders, URL=FakeURL)
    sys.modules['workers'] = types.SimpleNamespace(WorkerEntrypoint=FakeEntrypoint)
    spec = importlib.util.spec_from_file_location('blt_next_main', PROJECT / 'workers' / 'main.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


main = load_worker()


def fetch(path, method='GET', assets=None, body=None, headers=None):
    env = types.SimpleNamespace(ASSETS=assets or FakeAssets())
    request = FakeRequest('https://owaspblt.org' + path, method=method, body=body, headers=headers)
    return asyncio.run(main.Default(env).fetch(request))


# ---- tests --------------------------------------------------------------------------------

class LegacyRedirectTests(unittest.TestCase):
    def assertRedirect(self, path, expected, method='GET', status=301):
        response = fetch(path, method=method)
        self.assertEqual(response.status, status, path)
        self.assertEqual(response.headers.get('Location'), expected)

    def test_old_deep_links_redirect_with_path_and_query(self):
        cases = {
            '/issue/1/': '/issue/1/',
            '/issue/123/?ref=mail': '/issue/123/?ref=mail',
            '/profile/someone/': '/profile/someone/',
            '/domain/example.com/': '/domain/example.com/',
            '/leaderboard/': '/leaderboard/',
            '/leaderboard/monthly/?month=3&year=2024': '/leaderboard/monthly/?month=3&year=2024',
            '/report/': '/report/',
            '/api/v1/issues/': '/api/v1/issues/',
            '/api/v1/issues/?page=2': '/api/v1/issues/?page=2',
            '/api/trademarks/search/?query=blt': '/api/trademarks/search/?query=blt',
            '/accounts/login/': '/accounts/login/',
            '/authenticate/': '/authenticate/',
            '/organization/1/dashboard/': '/organization/1/dashboard/',
            '/hunt/7/': '/hunt/7/',
            '/bounties/': '/bounties/',
            '/scoreboard/': '/scoreboard/',
            '/gsoc/pr-report/': '/gsoc/pr-report/',
            '/hackathons/some-event/': '/hackathons/some-event/',
            '/upload/1/x.png': '/upload/1/x.png',
            '/leaderboard': '/leaderboard',
        }
        for path, target in cases.items():
            with self.subTest(path=path):
                self.assertRedirect(path, 'https://legacy.owaspblt.org' + target)

    def test_non_get_requests_keep_their_method(self):
        self.assertRedirect('/api/v1/issues/', 'https://legacy.owaspblt.org/api/v1/issues/', method='POST', status=308)
        self.assertRedirect('/authenticate/', 'https://legacy.owaspblt.org/authenticate/', method='POST', status=308)

    def test_head_is_a_301(self):
        self.assertRedirect('/issue/1/', 'https://legacy.owaspblt.org/issue/1/', method='HEAD')

    def test_redirect_host_is_fixed(self):
        # A path that looks like another host stays on legacy.owaspblt.org.
        target = main.legacy_redirect_target('/issue//evil.example/', '')
        self.assertTrue(target.startswith('https://legacy.owaspblt.org/'))
        self.assertEqual(main.legacy_redirect_target('//evil.example/x', ''), None)

    def test_segment_match_is_exact(self):
        for path in ('/issuezzz/', '/profiles-x', '/Issue/1/', '/api/v3/x', '/api/', '/api'):
            with self.subTest(path=path):
                self.assertIsNone(main.legacy_redirect_target(path, ''))


class OwnRoutesAreNotShadowedTests(unittest.TestCase):
    def test_blt_next_api_routes_still_answer(self):
        self.assertEqual(fetch('/api/stats').status, 200)
        self.assertEqual(fetch('/api/leaderboard').status, 200)
        self.assertEqual(fetch('/api/projects').status, 200)
        self.assertEqual(fetch('/api/bugs').status, 200)
        response = fetch('/api/auth/login', method='POST', body=json.dumps({'email': 'a@b.c', 'password': 'x'}))
        self.assertEqual(response.status, 200)

    def test_no_route_page_or_asset_matches_a_legacy_prefix(self):
        for method_routes in main.ROUTES.values():
            for path in method_routes:
                with self.subTest(route=path):
                    self.assertIsNone(main.legacy_redirect_target(path, ''))
        for file in (PROJECT / 'src').rglob('*'):
            if file.is_file():
                rel = '/' + file.relative_to(PROJECT / 'src').as_posix()
                with self.subTest(asset=rel):
                    self.assertIsNone(main.legacy_redirect_target(rel, ''))
                    if rel.endswith('.html'):
                        self.assertIsNone(main.legacy_redirect_target(rel[:-5], ''))

    def test_home_and_assets_are_served(self):
        self.assertEqual(fetch('/').status, 200)
        self.assertEqual(fetch('/pages/about').status, 200)

    def test_root_level_files_are_not_redirected(self):
        for path in ('/', '/favicon.ico', '/robots.txt', '/.well-known/security.txt', '/__debug__/', '/500/'):
            with self.subTest(path=path):
                self.assertIsNone(main.legacy_redirect_target(path, ''))


class NotFoundTests(unittest.TestCase):
    def test_unknown_page_is_a_clean_html_404(self):
        assets = FakeAssets()
        response = fetch('/zzz-nope', assets=assets)
        self.assertEqual(response.status, 404)
        self.assertIn('text/html', response.headers.get('Content-Type'))
        self.assertIn('Page not found', response.body)
        self.assertEqual(len(assets.calls), 1)  # the original Request was passed through

    def test_missing_asset_is_a_404(self):
        self.assertEqual(fetch('/assets/css/nope.css').status, 404)

    def test_unknown_api_path_is_a_json_404(self):
        response = fetch('/api/nope')
        self.assertEqual(response.status, 404)
        self.assertEqual(json.loads(response.body)['error'], 'Not found')

    def test_unknown_post_does_not_touch_assets(self):
        assets = FakeAssets()
        response = fetch('/nope', method='POST', assets=assets)
        self.assertEqual(response.status, 404)
        self.assertEqual(assets.calls, [])

    def test_asset_errors_still_give_a_404(self):
        class BrokenAssets(FakeAssets):
            async def fetch(self, request):
                raise RuntimeError('boom')

        self.assertEqual(fetch('/nope', assets=BrokenAssets()).status, 404)


class LegacyRouteListTests(unittest.TestCase):
    """The allowlist should cover every top-level route of the legacy Django app."""

    DELIBERATELY_SKIPPED = {'', 'api', '.well-known', '__debug__', '500', 'test-sentry', 'favicon.ico', 'robots.txt'}

    def legacy_urls(self):
        for name in ('blt-legacy',):
            path = PROJECT.parent / name / 'blt' / 'urls.py'
            if path.exists():
                return path.read_text()
        self.skipTest('legacy app folder not found')

    def test_every_legacy_segment_is_covered(self):
        source = self.legacy_urls()
        missing = set()
        for raw in re.findall(r'\b(?:re_)?path\(\s*r?["\']([^"\']*)["\']', source):
            path = raw.lstrip('^')
            first = path.split('/')[0]
            first = first.replace('\\.', '.').rstrip('$')
            if first.startswith('<') or first.startswith('swagger('):
                continue  # included apps' slugs; swagger.json/yaml are listed by hand
            if first == 'api':
                second = path.split('/')[1] if '/' in path else ''
                if second and not second.startswith('<') and second != 'debug' and second not in main.LEGACY_API_SEGMENTS:
                    missing.add('api/' + second)
                continue
            if first not in main.LEGACY_SEGMENTS and first not in self.DELIBERATELY_SKIPPED:
                missing.add(first)
        self.assertEqual(missing, set())


if __name__ == '__main__':
    unittest.main()
