"""Tests for /api/bugs: validation, forwarding to blt-api (mocked), errors and rate limits.

Run with: python3 -m unittest discover -s tests
"""
import asyncio
import json
import sys
import types
import unittest
from urllib.parse import urlencode

from test_routing import FakeAssets, FakeHeaders, FakeRequest, main

VALID = {
    'title': 'XSS in search',
    'url': 'https://example.com/search?q=1',
    'severity': 'high',
    'type': 'security',
    'description': 'The q parameter is reflected without escaping.',
    'steps': '1. Open /search?q=<script>\n2. See alert',
    'website': '',
}

FORM = 'application/x-www-form-urlencoded'


class BodyRequest(FakeRequest):
    async def text(self):
        return self._body or ''


class FakeApiResponse:
    def __init__(self, status, data=None, raw=None):
        self.status = status
        self._text = raw if raw is not None else (json.dumps(data) if data is not None else '')

    async def text(self):
        return self._text


class FakeBltApi:
    """Stands in for the BLT_API service binding."""

    def __init__(self, status=201, data=None, raw=None, error=None):
        self.calls = []
        self.status = status
        self.data = data if data is not None else {
            'success': True,
            'message': 'Bug created successfully',
            'data': {'id': 42, 'title': 'XSS in search', 'url': 'https://example.com/search?q=1',
                     'severity': 'high', 'bug_type': 'security', 'status': 'open',
                     'created': '2026-10-21 10:00:00', 'reporter_ip_address': '203.0.113.9',
                     'user_agent': 'UA'},
        }
        self.raw = raw
        self.error = error

    async def fetch(self, url, **init):
        # Same signature as the Python SDK's binding.fetch: URL, then keyword options.
        self.calls.append((url, init))
        if self.error:
            raise self.error
        return FakeApiResponse(self.status, self.data, self.raw)


class FakeLimiter:
    def __init__(self, success=True, error=None):
        self.success = success
        self.error = error
        self.keys = []

    async def limit(self, options):
        if self.error:
            raise self.error
        self.keys.append(options['key'])
        return {'success': self.success}


def make_env(api=None, key='test-key', limiter=None, **extra):
    env = types.SimpleNamespace(ASSETS=FakeAssets())
    if api is not None:
        env.BLT_API = api
    if key is not None:
        env.BLT_API_KEY = key
    if limiter is not None:
        env.BUG_REPORT_LIMITER = limiter
    for name, value in extra.items():
        setattr(env, name, value)
    return env


def post(env, fields=None, body=None, content_type=FORM, accept='application/json', origin=None, ip='198.51.100.7', path='/api/bugs'):
    headers = {'Content-Type': content_type, 'CF-Connecting-IP': ip, 'User-Agent': 'TestBrowser/1.0'}
    if accept:
        headers['Accept'] = accept
    if origin:
        headers['Origin'] = origin
    if body is None:
        body = urlencode(fields if fields is not None else VALID)
    request = BodyRequest('https://next.owaspblt.org' + path, method='POST', headers=headers, body=body)
    return asyncio.run(main.Default(env).fetch(request))


def get(env, path='/api/bugs'):
    request = BodyRequest('https://next.owaspblt.org' + path, method='GET', headers={'Accept': 'application/json'})
    return asyncio.run(main.Default(env).fetch(request))


def body_of(response):
    return json.loads(response.body)


class BugReportTestCase(unittest.TestCase):
    def setUp(self):
        main._bug_rate_memory.clear()


class SubmitTests(BugReportTestCase):
    def test_form_post_is_forwarded_to_blt_api(self):
        api = FakeBltApi()
        response = post(make_env(api))
        self.assertEqual(response.status, 201)
        data = body_of(response)
        self.assertEqual(data['success'], True)
        self.assertEqual(data['id'], 42)
        self.assertEqual(data['link'], '/pages/bugs.html?id=42')
        self.assertNotIn('reporter_ip_address', data['bug'])
        self.assertEqual(response.headers.get('Cache-Control'), 'no-store')

        self.assertEqual(len(api.calls), 1)
        url, init = api.calls[0]
        self.assertEqual(url, 'https://api.owaspblt.org/bugs')
        self.assertEqual(init['method'], 'POST')
        self.assertEqual(init['headers']['X-BLT-API-Key'], 'test-key')
        self.assertEqual(init['headers']['Content-Type'], 'application/json')
        self.assertEqual(init['headers']['X-Forwarded-For'], '198.51.100.7')
        self.assertEqual(json.loads(init['body']), {
            'url': 'https://example.com/search?q=1',
            'title': 'XSS in search',
            'description': 'The q parameter is reflected without escaping.',
            'severity': 'high',
            'bug_type': 'security',
            'steps_to_reproduce': '1. Open /search?q=<script>\n2. See alert',
            'user_agent': 'TestBrowser/1.0',
        })

    def test_json_post_is_accepted(self):
        api = FakeBltApi()
        response = post(make_env(api), body=json.dumps(VALID), content_type='application/json')
        self.assertEqual(response.status, 201)
        self.assertEqual(json.loads(api.calls[0][1]['body'])['bug_type'], 'security')

    def test_steps_are_optional_and_values_are_trimmed(self):
        api = FakeBltApi()
        fields = dict(VALID, steps='', title='  XSS  ', severity='HIGH')
        self.assertEqual(post(make_env(api), fields).status, 201)
        sent = json.loads(api.calls[0][1]['body'])
        self.assertNotIn('steps_to_reproduce', sent)
        self.assertEqual(sent['title'], 'XSS')
        self.assertEqual(sent['severity'], 'high')

    def test_post_without_javascript_gets_an_html_page(self):
        response = post(make_env(FakeBltApi()), accept='text/html')
        self.assertEqual(response.status, 201)
        self.assertIn('text/html', response.headers.get('Content-Type'))
        self.assertIn('Report submitted', response.body)
        self.assertIn('/pages/bugs.html?id=42', response.body)

    def test_html_error_page_escapes_messages(self):
        api = FakeBltApi(status=400, data={'error': True, 'message': '<b>bad</b>'})
        response = post(make_env(api), accept='text/html')
        self.assertEqual(response.status, 400)
        self.assertIn('&lt;b&gt;bad&lt;/b&gt;', response.body)
        self.assertNotIn('<b>bad</b>', response.body)


class ValidationTests(BugReportTestCase):
    def assertRejected(self, fields, status=400, field=None, **kwargs):
        api = FakeBltApi()
        response = post(make_env(api), fields, **kwargs)
        self.assertEqual(response.status, status, fields)
        data = body_of(response)
        self.assertFalse(data['success'])
        self.assertTrue(data['error'])
        if field:
            self.assertEqual(data.get('field'), field)
        self.assertEqual(api.calls, [], 'invalid reports must not reach blt-api')
        return data

    def test_required_fields(self):
        for name in ('title', 'url', 'description', 'severity', 'type'):
            with self.subTest(missing=name):
                fields = dict(VALID)
                del fields[name]
                self.assertRejected(fields, field=name)
        with self.subTest('whitespace only'):
            self.assertRejected(dict(VALID, description='   \n  '), field='description')

    def test_url_must_be_http_or_https(self):
        for url in ('javascript:alert(1)', 'ftp://example.com/x', 'example.com', 'http://', 'https://exa mple.com',
                    'data:text/html,hi', '//example.com/x'):
            with self.subTest(url=url):
                self.assertRejected(dict(VALID, url=url), field='url')

    def test_length_caps(self):
        self.assertRejected(dict(VALID, title='x' * 201), field='title')
        self.assertRejected(dict(VALID, url='https://example.com/' + 'a' * 200), field='url')
        self.assertRejected(dict(VALID, description='x' * 5001), field='description')
        self.assertRejected(dict(VALID, steps='x' * 5001), field='steps')

    def test_body_size_cap(self):
        self.assertRejected(None, status=413, body='title=' + 'x' * (40 * 1024))

    def test_choices(self):
        self.assertRejected(dict(VALID, severity='urgent'), field='severity')
        self.assertRejected(dict(VALID, type='<script>'), field='type')

    def test_honeypot(self):
        data = self.assertRejected(dict(VALID, website='http://spam.example'))
        self.assertNotIn('field', data)  # don't point bots at the trap

    def test_bad_json(self):
        self.assertRejected(None, body='{nope', content_type='application/json')
        self.assertRejected(None, body='[1, 2]', content_type='application/json')
        self.assertRejected(None, body=json.dumps(dict(VALID, title={'x': 1})), content_type='application/json')

    def test_multipart_is_refused(self):
        self.assertRejected(None, status=415, body='--x--', content_type='multipart/form-data; boundary=x')

    def test_cross_site_posts_are_refused(self):
        self.assertRejected(VALID, status=403, origin='https://evil.example')

    def test_own_origins_are_allowed(self):
        for origin in ('https://next.owaspblt.org', 'https://owaspblt.org', 'https://www.owaspblt.org'):
            with self.subTest(origin=origin):
                main._bug_rate_memory.clear()
                self.assertEqual(post(make_env(FakeBltApi()), origin=origin).status, 201)


class UpstreamErrorTests(BugReportTestCase):
    def test_missing_secret_is_a_503_and_nothing_is_sent(self):
        api = FakeBltApi()
        response = post(make_env(api, key=None))
        self.assertEqual(response.status, 503)
        self.assertIn('not configured', body_of(response)['error'])
        self.assertEqual(api.calls, [])

    def test_blt_api_validation_message_is_shown(self):
        api = FakeBltApi(status=400, data={'error': True, 'message': 'URL must include a valid domain', 'status': 400})
        response = post(make_env(api))
        self.assertEqual(response.status, 400)
        self.assertEqual(body_of(response)['error'], 'URL must include a valid domain')

    def test_blt_api_auth_failure_is_a_502(self):
        for status in (401, 403):
            with self.subTest(status=status):
                main._bug_rate_memory.clear()
                api = FakeBltApi(status=status, data={'error': True, 'message': 'Invalid API key'})
                response = post(make_env(api))
                self.assertEqual(response.status, 502)
                self.assertIn('misconfigured', body_of(response)['error'])

    def test_blt_api_server_error_does_not_leak_details(self):
        api = FakeBltApi(status=500, data={'error': True, 'message': 'Failed to create bug: D1_ERROR secret stuff'})
        response = post(make_env(api))
        self.assertEqual(response.status, 502)
        self.assertNotIn('D1_ERROR', response.body)

    def test_blt_api_rate_limit_is_passed_on(self):
        api = FakeBltApi(status=429, data={'error': True, 'message': 'Too many requests.'})
        self.assertEqual(post(make_env(api)).status, 429)

    def test_unparseable_or_unsuccessful_answers_are_failures(self):
        for api in (FakeBltApi(status=201, raw='<html>oops</html>'), FakeBltApi(status=200, data={'success': False})):
            with self.subTest(api=api.raw or api.data):
                main._bug_rate_memory.clear()
                self.assertEqual(post(make_env(api)).status, 502)

    def test_network_error_is_a_502(self):
        api = FakeBltApi(error=RuntimeError('connection reset'))
        response = post(make_env(api))
        self.assertEqual(response.status, 502)
        self.assertIn("Couldn't reach", body_of(response)['error'])

    def test_without_binding_it_fetches_blt_api_url(self):
        calls = []

        async def fake_fetch(url, init):
            calls.append((url, init))
            return FakeApiResponse(201, FakeBltApi().data)

        sys.modules['js'].fetch = fake_fetch
        try:
            response = post(make_env(api=None, BLT_API_URL='https://blt-api.example.workers.dev/'))
        finally:
            del sys.modules['js'].fetch
        self.assertEqual(response.status, 201)
        self.assertEqual(calls[0][0], 'https://blt-api.example.workers.dev/bugs')


class RateLimitTests(BugReportTestCase):
    def test_in_memory_limit_per_ip(self):
        api = FakeBltApi()
        env = make_env(api)
        for _ in range(main.BUG_RATE_LIMIT):
            self.assertEqual(post(env).status, 201)
        response = post(env)
        self.assertEqual(response.status, 429)
        self.assertIn('Too many', body_of(response)['error'])
        self.assertEqual(len(api.calls), main.BUG_RATE_LIMIT)
        self.assertEqual(post(env, ip='198.51.100.8').status, 201)  # other IPs are unaffected

    def test_invalid_reports_do_not_use_up_the_limit(self):
        env = make_env(FakeBltApi())
        for _ in range(main.BUG_RATE_LIMIT + 2):
            post(env, dict(VALID, url='nope'))
        self.assertEqual(post(env).status, 201)

    def test_rate_limit_binding_is_used(self):
        limiter = FakeLimiter(success=False)
        api = FakeBltApi()
        self.assertEqual(post(make_env(api, limiter=limiter)).status, 429)
        self.assertEqual(limiter.keys, ['198.51.100.7'])
        self.assertEqual(api.calls, [])
        self.assertEqual(post(make_env(api, limiter=FakeLimiter(success=True))).status, 201)

    def test_broken_binding_falls_back_to_memory(self):
        env = make_env(FakeBltApi(), limiter=FakeLimiter(error=RuntimeError('down')))
        statuses = [post(env).status for _ in range(main.BUG_RATE_LIMIT + 1)]
        self.assertEqual(statuses[-1], 429)


class ReadTests(BugReportTestCase):
    LIST = {
        'success': True,
        'data': [
            {'id': 9, 'url': 'https://a.example', 'title': 'A', 'description': 'secret detail', 'is_hidden': 0,
             'severity': 'low', 'bug_type': 'ui', 'status': 'open', 'created': '2026-10-01 00:00:00'},
            {'id': 8, 'url': 'https://b.example', 'title': 'Hidden', 'description': 'x', 'is_hidden': 1},
        ],
        'pagination': {'total': 2},
    }

    def test_recent_list_hides_hidden_reports_and_extra_fields(self):
        api = FakeBltApi(status=200, data=self.LIST)
        response = get(make_env(api))
        self.assertEqual(response.status, 200)
        data = body_of(response)
        self.assertEqual([b['id'] for b in data['bugs']], [9])
        self.assertNotIn('description', data['bugs'][0])
        self.assertEqual(api.calls[0][0], 'https://api.owaspblt.org/bugs?per_page=20')
        self.assertEqual(api.calls[0][1]['method'], 'GET')
        self.assertNotIn('body', api.calls[0][1])
        self.assertIn('max-age', response.headers.get('Cache-Control'))

    def test_one_report_drops_private_fields(self):
        bug = {'id': 42, 'title': 'T', 'url': 'https://e.example', 'description': 'D', 'steps_to_reproduce': 'S',
               'reporter_ip_address': '203.0.113.9', 'user_agent': 'UA', 'is_hidden': 0, 'user': 3}
        api = FakeBltApi(status=200, data={'success': True, 'data': bug})
        response = get(make_env(api), '/api/bugs?id=42')
        self.assertEqual(response.status, 200)
        shown = body_of(response)['bug']
        self.assertEqual(shown['description'], 'D')
        for private in ('reporter_ip_address', 'user_agent', 'user', 'is_hidden'):
            self.assertNotIn(private, shown)
        self.assertEqual(api.calls[0][0], 'https://api.owaspblt.org/bugs/42')

    def test_hidden_or_missing_report_is_a_404(self):
        hidden = FakeBltApi(status=200, data={'success': True, 'data': {'id': 5, 'is_hidden': 1}})
        self.assertEqual(get(make_env(hidden), '/api/bugs?id=5').status, 404)
        missing = FakeBltApi(status=404, data={'error': True, 'message': 'Bug not found'})
        self.assertEqual(get(make_env(missing), '/api/bugs?id=5').status, 404)

    def test_bad_id_is_a_400_without_calling_blt_api(self):
        api = FakeBltApi()
        for path in ('/api/bugs?id=abc', '/api/bugs?id=1%2F..%2Fusers', '/api/bugs?id=' + '9' * 13):
            with self.subTest(path=path):
                self.assertEqual(get(make_env(api), path).status, 400)
        self.assertEqual(api.calls, [])


class OriginListTests(unittest.TestCase):
    def test_allowed_origins_are_spelled_right(self):
        self.assertIn('https://next.owaspblt.org', main.ALLOWED_ORIGINS)
        self.assertFalse([o for o in main.ALLOWED_ORIGINS if 'owaspbt.' in o])


if __name__ == '__main__':
    unittest.main()
