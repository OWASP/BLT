"""
Integration tests for the BLT-Sizzle API.
Runs against the deployed Worker when SIZZLE_URL is set.
All tests are read-only / non-destructive.
"""
import os
import sys
import json
import unittest
import urllib.request
import urllib.error

BASE_URL = os.environ.get("SIZZLE_URL", "").rstrip("/")
RUN_NETWORK_TESTS = bool(BASE_URL)
NETWORK_TEST_REASON = "Set SIZZLE_URL to run deployed Worker integration tests"


def get(path, *, allow_redirects=False):
    """Perform a GET request, optionally following redirects."""
    url = BASE_URL + path
    req = urllib.request.Request(url, headers={"User-Agent": "sizzle-test/1.0"})
    try:
        response = urllib.request.urlopen(req, timeout=15)
        return response.status, dict(response.headers), response.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode()
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connection failed for {url}: {e.reason}") from e


def get_no_redirect(path):
    """Perform a GET that does NOT follow redirects; returns (status, headers)."""
    import http.client
    from urllib.parse import urlparse
    parsed = urlparse(BASE_URL + path)
    host = parsed.netloc
    use_https = parsed.scheme == "https"
    conn_cls = http.client.HTTPSConnection if use_https else http.client.HTTPConnection
    conn = conn_cls(host, timeout=15)
    conn.request("GET", parsed.path + ("?" + parsed.query if parsed.query else ""),
                 headers={"User-Agent": "sizzle-test/1.0"})
    resp = conn.getresponse()
    headers = {k.lower(): v for k, v in resp.getheaders()}
    body = resp.read().decode()
    conn.close()
    return resp.status, headers, body


@unittest.skipUnless(RUN_NETWORK_TESTS, NETWORK_TEST_REASON)
class TestHomepage(unittest.TestCase):
    def test_homepage_returns_200(self):
        status, headers, body = get("/")
        self.assertEqual(status, 200, f"Expected 200 but got {status}")

    def test_homepage_is_html(self):
        status, headers, body = get("/")
        ct = headers.get("Content-Type", headers.get("content-type", ""))
        self.assertIn("text/html", ct, f"Unexpected Content-Type: {ct}")

    def test_homepage_contains_sizzle_branding(self):
        status, headers, body = get("/")
        self.assertIn("SIZZLE", body.upper(),
                      "Homepage body does not contain 'SIZZLE'")

    def test_homepage_contains_github_login(self):
        status, headers, body = get("/")
        self.assertIn("github.com/login/oauth/authorize", body.lower() + body,
                      "No GitHub OAuth link found. "
                      "Check that Login with GitHub button is present.")


@unittest.skipUnless(RUN_NETWORK_TESTS, NETWORK_TEST_REASON)
class TestAuthEndpoints(unittest.TestCase):
    def test_auth_login_redirects_to_github(self):
        status, headers, body = get_no_redirect("/api/auth/login")
        self.assertIn(status, (301, 302, 307, 308),
                      f"Expected a redirect but got {status}")
        location = headers.get("location", "")
        self.assertIn("github.com/login/oauth/authorize", location,
                      f"Redirect does not point to GitHub: {location}")

    def test_auth_me_returns_401_when_not_authenticated(self):
        status, headers, body = get("/api/auth/me")
        self.assertEqual(status, 401, f"Expected 401 but got {status}: {body}")
        data = json.loads(body)
        self.assertFalse(data.get("authenticated"),
                         "Expected authenticated=false")

    def test_dashboard_api_returns_401_when_not_authenticated(self):
        status, headers, body = get("/api/dashboard")
        self.assertEqual(status, 401, f"Expected 401 but got {status}: {body}")
        data = json.loads(body)
        self.assertIn("error", data)

    def test_callback_without_params_redirects_with_error(self):
        status, headers, body = get_no_redirect("/api/auth/callback")
        self.assertIn(status, (301, 302, 307, 308),
                      f"Expected redirect but got {status}")
        location = headers.get("location", "")
        self.assertIn("auth_error", location,
                      f"Expected auth_error in redirect but got: {location}")

    def test_callback_with_bad_state_redirects_with_error(self):
        status, headers, body = get_no_redirect(
            "/api/auth/callback?code=fakecode&state=fakestate"
        )
        self.assertIn(status, (301, 302, 307, 308),
                      f"Expected redirect but got {status}")
        location = headers.get("location", "")
        self.assertIn("auth_error", location,
                      f"Expected auth_error in redirect but got: {location}")


@unittest.skipUnless(RUN_NETWORK_TESTS, NETWORK_TEST_REASON)
class TestPublicApiEndpoints(unittest.TestCase):
    def test_leaderboard_returns_200_json(self):
        status, headers, body = get("/api/leaderboard")
        self.assertEqual(status, 200, f"Expected 200 but got {status}: {body}")
        ct = headers.get("Content-Type", headers.get("content-type", ""))
        self.assertIn("application/json", ct)
        data = json.loads(body)
        self.assertIn("leaderboard", data)
        self.assertIsInstance(data["leaderboard"], list)

    def test_unknown_api_route_returns_404(self):
        status, headers, body = get("/api/nonexistent")
        self.assertEqual(status, 404, f"Expected 404 but got {status}")
        data = json.loads(body)
        self.assertIn("error", data)


@unittest.skipUnless(RUN_NETWORK_TESTS, NETWORK_TEST_REASON)
class TestStaticAssets(unittest.TestCase):
    def test_leaderboard_page_returns_200(self):
        status, headers, body = get("/leaderboard")
        self.assertEqual(status, 200, f"Expected 200 but got {status}")

    def test_dashboard_page_redirects_to_login_when_not_authenticated(self):
        status, headers, body = get_no_redirect("/dashboard")
        self.assertIn(status, (301, 302, 307, 308),
                      f"Expected redirect but got {status}")
        location = headers.get("location", "")
        self.assertEqual(location, "/login",
                         f"Expected redirect to /login but got: {location}")

@unittest.skipUnless(RUN_NETWORK_TESTS, NETWORK_TEST_REASON)
class TestAuthRedirectLoop(unittest.TestCase):
    """
    Verify that landing on the homepage after an OAuth failure does NOT
    redirect back to GitHub, i.e. the old server-side auth gate loop is gone.
    """

    def _get_final_status(self, path):
        """Follow redirects (via urllib default) and return the final HTTP status."""
        try:
            status, headers, body = get(path)
            return status
        except Exception as e:
            raise AssertionError(f"Request to {path} raised: {e}") from e

    def test_homepage_auth_error_token_failed_returns_200(self):
        status = self._get_final_status("/?auth_error=token_failed")
        self.assertEqual(status, 200,
                         f"/?auth_error=token_failed ended up with status {status} "
                         "(redirect loop or server error?)")

    def test_homepage_auth_error_server_error_returns_200(self):
        status = self._get_final_status("/?auth_error=server_error")
        self.assertEqual(status, 200,
                         f"/?auth_error=server_error ended up with status {status}")

    def test_homepage_auth_error_not_configured_returns_200(self):
        status = self._get_final_status("/?auth_error=not_configured")
        self.assertEqual(status, 200,
                         f"/?auth_error=not_configured ended up with status {status}")

class TestWorkerSyntax(unittest.TestCase):
    """Verify the worker Python source compiles without errors."""
    def test_worker_main_py_syntax(self):
        import ast
        worker_path = os.path.join(
            os.path.dirname(__file__), "..", "workers", "main.py"
        )
        with open(worker_path, "r") as f:
            source = f.read()
        try:
            ast.parse(source)
        except SyntaxError as e:
            self.fail(f"Syntax error in workers/main.py: {e}")

    def test_worker_scheduler_py_syntax(self):
        import ast
        scheduler_path = os.path.join(
            os.path.dirname(__file__), "..", "workers", "scheduler.py"
        )
        if not os.path.exists(scheduler_path):
            self.skipTest("scheduler.py not found")
        with open(scheduler_path, "r") as f:
            source = f.read()
        try:
            ast.parse(source)
        except SyntaxError as e:
            self.fail(f"Syntax error in workers/scheduler.py: {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
