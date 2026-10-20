import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "workers" / "main.py"
sys.path.insert(0, str(ROOT / "workers"))

from url_safety import is_slack_webhook_url  # noqa: E402


class TestSlackWebhookUrl(unittest.TestCase):
    def test_only_hooks_slack_com_services(self):
        self.assertTrue(is_slack_webhook_url("https://hooks.slack.com/services/T0/B0/xyz"))
        for bad in [
            "http://hooks.slack.com/services/T0/B0/xyz",
            "https://hooks.slack.com.evil.example/services/x",
            "https://evil.example/services/x",
            "https://user@hooks.slack.com/services/x",
            "https://hooks.slack.com:8443/services/x",
            "https://hooks.slack.com/other",
            'https://hooks.slack.com/services/x"',
            "http://127.0.0.1/services/x",
            "",
            None,
        ]:
            self.assertFalse(is_slack_webhook_url(bad), bad)


class TestNotificationAndOAuthContract(unittest.TestCase):
    def setUp(self):
        self.source = MAIN.read_text()

    def body(self, start, end):
        return self.source[self.source.index(start):self.source.index(end)]

    def test_test_notification_uses_the_session_user(self):
        body = self.body("async def handle_test_notification", "async def handle_debug_db")
        self.assertIn("get_session_user(request, env)", body)
        self.assertNotIn("searchParams.get('userId')", body)
        self.assertIn("is_slack_webhook_url(slack_webhook_url)", body)

    def test_settings_validate_the_webhook_url(self):
        body = self.body("async def handle_save_settings", "async def handle_test_notification")
        self.assertIn("is_slack_webhook_url(slack_webhook_url)", body)

    def test_no_hardcoded_encryption_key_fallback(self):
        self.assertNotIn("sizzle-dev-key", self.source)

    def test_oauth_state_is_bound_to_a_cookie(self):
        login = self.body("async def handle_auth_login", "async def handle_auth_callback")
        self.assertIn("OAUTH_STATE_COOKIE", login)
        callback = self.source[self.source.index("async def handle_auth_callback"):]
        self.assertRegex(callback, r"oauth_state_matches_cookie\(request\.headers\.get\('Cookie'\)")

    def test_state_cookie_comparison(self):
        start = self.source.index('OAUTH_STATE_COOKIE = "sizzle_oauth_state"')
        end = self.source.index("async def handle_auth_login")
        namespace = {}
        exec("import hmac\n" + self.source[start:end], namespace)
        match = namespace["oauth_state_matches_cookie"]
        self.assertTrue(match("a=b; sizzle_oauth_state=abc", "abc"))
        self.assertFalse(match("sizzle_oauth_state=abc", "abd"))
        self.assertFalse(match("", "abc"))
        self.assertFalse(match("sizzle_oauth_state=", ""))


if __name__ == "__main__":
    unittest.main()
