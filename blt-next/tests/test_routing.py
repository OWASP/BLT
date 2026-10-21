"""Routing tests for workers/main.py: old-site links, the /moved page, own routes and the 404 page.

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
from urllib.parse import quote, unquote, urlsplit

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

class OldSiteLinkTests(unittest.TestCase):
    def assertMoved(self, path, method='GET'):
        response = fetch(path, method=method)
        self.assertEqual(response.status, 302, path)
        location = response.headers.get('Location')
        self.assertTrue(location.startswith('/moved?from='), location)
        self.assertEqual(unquote(location[len('/moved?from='):]), path)
        return location

    def test_old_page_links_go_to_the_moved_page_with_path_and_query(self):
        for path in ('/issue/1/', '/issue/123/?ref=mail', '/profile/someone/', '/domain/example.com/',
                     '/leaderboard/', '/leaderboard/monthly/?month=3&year=2024', '/report/', '/accounts/login/',
                     '/authenticate/', '/organization/1/dashboard/', '/hunt/7/', '/bounties/', '/scoreboard/',
                     '/gsoc/pr-report/', '/hackathons/some-event/', '/upload/1/x.png', '/leaderboard'):
            with self.subTest(path=path):
                self.assertMoved(path)

    def test_head_and_post_also_go_to_the_moved_page(self):
        self.assertMoved('/issue/1/', method='HEAD')
        self.assertMoved('/report/', method='POST')

    def test_old_api_paths_get_json_not_a_redirect(self):
        for path in ('/api/v1/issues/', '/api/v1/issues/?page=2', '/api/v2/hunts/', '/api/trademarks/search/'):
            with self.subTest(path=path):
                response = fetch(path)
                self.assertEqual(response.status, 404)
                data = json.loads(response.body)
                self.assertIn('old BLT API', data['error'])
                self.assertEqual(data['api'], 'https://api.owaspblt.org')
        self.assertEqual(fetch('/api/v1/createissues/', method='POST').status, 404)

    def test_moved_page_names_the_new_home(self):
        cases = {
            '/leaderboard/': 'https://pool.owaspblt.org/leaderboard',
            '/hackathons/x/': 'https://hackathons.owaspblt.org/',
            '/gsoc/pr-report/': 'https://gsoc.owaspblt.org/',
            '/jobs/': 'https://jobs.owaspblt.org/',
            '/education/': 'https://university.owaspblt.org/',
            '/sizzle/': 'https://sizzle.owaspblt.org/',
            '/report/': '/pages/report-bug',
        }
        for path, home in cases.items():
            with self.subTest(path=path):
                response = fetch(self.assertMoved(path))
                self.assertEqual(response.status, 200)
                self.assertIn(f'href="{home}"', response.body)
                self.assertIn('This page has moved', response.body)
                self.assertIn('href="/pages/report-bug"', response.body)
                self.assertIn('back after the migration', response.body)

    def test_moved_page_without_a_new_home(self):
        body = fetch(self.assertMoved('/issue/1/')).body
        self.assertIn('<code>/issue/1/</code>', body)
        self.assertIn("doesn't have a new home yet", body)

    def test_moved_page_escapes_its_parameter(self):
        body = fetch('/moved?from=' + quote('/issue/<script>alert(1)</script>/')).body
        self.assertNotIn('<script>', body)
        self.assertIn('&lt;script&gt;', body)
        # A from= that isn't an old-site path is not echoed at all.
        body = fetch('/moved?from=' + quote('javascript:alert(1)')).body
        self.assertNotIn('javascript:', body)
        self.assertEqual(fetch('/moved').status, 200)

    def test_every_new_home_is_reachable(self):
        for segments, label, url in main.NEW_HOMES:
            self.assertTrue(url.startswith(('https://', '/pages/')), url)
            for segment in segments:
                with self.subTest(segment=segment):
                    self.assertTrue(main.is_legacy_path('/' + segment + '/'), segment)

    def test_redirect_never_leaves_the_site(self):
        self.assertFalse(main.is_legacy_path('//evil.example/x'))
        self.assertTrue(main.moved_location('/issue//evil.example/', '').startswith('/moved?from='))

    def test_segment_match_is_exact(self):
        for path in ('/issuezzz/', '/profiles-x', '/Issue/1/', '/api/v3/x', '/api/', '/api', '/moved'):
            with self.subTest(path=path):
                self.assertFalse(main.is_legacy_path(path))


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
                    self.assertFalse(main.is_legacy_path(path))
        for file in (PROJECT / 'src').rglob('*'):
            if file.is_file():
                rel = '/' + file.relative_to(PROJECT / 'src').as_posix()
                with self.subTest(asset=rel):
                    self.assertFalse(main.is_legacy_path(rel))
                    if rel.endswith('.html'):
                        self.assertFalse(main.is_legacy_path(rel[:-5]))

    def test_home_and_assets_are_served(self):
        self.assertEqual(fetch('/').status, 200)
        self.assertEqual(fetch('/pages/about').status, 200)

    def test_root_level_files_are_not_redirected(self):
        for path in ('/', '/favicon.ico', '/robots.txt', '/.well-known/security.txt', '/__debug__/', '/500/'):
            with self.subTest(path=path):
                self.assertFalse(main.is_legacy_path(path))


class NotFoundTests(unittest.TestCase):
    def test_unknown_page_is_a_clean_html_404(self):
        assets = FakeAssets()
        response = fetch('/zzz-nope', assets=assets)
        self.assertEqual(response.status, 404)
        self.assertIn('text/html', response.headers.get('Content-Type'))
        self.assertIn('Page not found', response.body)
        self.assertNotIn('legacy.owaspblt.org', response.body)
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
