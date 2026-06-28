import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "workers" / "main.py"
SETTINGS = ROOT / "src" / "pages" / "settings.html"
PROFILE = ROOT / "src" / "pages" / "profile.html"
TIMEZONES = ROOT / "workers" / "timezones.py"


class TestProfileSettingsContract(unittest.TestCase):
    def setUp(self):
        self.source = MAIN.read_text()
        self.normalized = re.sub(r"\s+", " ", self.source)

    def test_profile_and_timezone_routes_are_registered(self):
        self.assertIn('"/api/profile" and method == "GET"', self.source)
        self.assertIn('"/api/profile" and method == "POST"', self.source)
        self.assertIn('"/api/timezones" and method == "GET"', self.source)
        self.assertIn("handle_get_profile", self.source)
        self.assertIn("handle_save_profile", self.source)
        self.assertIn("handle_get_timezones", self.source)

    def test_settings_use_session_identity_not_user_id_query_or_body(self):
        start = self.source.index("async def handle_get_settings")
        end = self.source.index("async def handle_save_settings")
        get_body = self.source[start:end]
        save_start = self.source.index("async def handle_save_settings")
        save_end = self.source.index("async def handle_test_notification")
        save_body = self.source[save_start:save_end]

        self.assertIn("get_session_user(request, env)", get_body)
        self.assertIn("get_session_user(request, env)", save_body)
        self.assertNotIn("url.searchParams.get('userId')", get_body)
        self.assertNotIn("data.get('userId')", save_body)
        self.assertIn("Unauthorized", get_body)
        self.assertIn("Unauthorized", save_body)

    def test_profile_api_returns_verification_and_timezone_state(self):
        start = self.source.index("async def handle_get_profile")
        end = self.source.index("async def handle_save_profile")
        body = self.source[start:end]
        for token in ["emailVerified", "needsEmailVerification", "displayName", "timezone", "notificationTime"]:
            self.assertIn(token, body)
        self.assertIn("encrypted_display_name", body)
        self.assertIn("get_auth_secret(env, \"ENCRYPTION_KEY\")", body)

    def test_timezone_validation_is_centralized_and_rejects_invalid_values(self):
        self.assertTrue(TIMEZONES.exists(), "workers/timezones.py must contain the canonical timezone list")
        tz_source = TIMEZONES.read_text()
        self.assertIn("VALID_TIMEZONES", tz_source)
        self.assertIn('"UTC"', tz_source)
        self.assertIn('"America/New_York"', tz_source)
        self.assertIn('"Asia/Kolkata"', tz_source)
        self.assertGreater(tz_source.count('"'), 800, "timezone list should include the IANA catalog, not a tiny sample")
        self.assertIn("is_valid_timezone", self.source)
        self.assertIn("Invalid timezone", self.source)

    def test_settings_page_has_all_timezone_dropdown_and_real_api_hooks(self):
        html = SETTINGS.read_text()
        self.assertIn('id="timezoneSelect"', html)
        self.assertIn('<select', html)
        self.assertIn("Intl.supportedValuesOf('timeZone')", html)
        self.assertIn("fallbackTimezones", html)
        self.assertIn("/api/timezones", html)
        self.assertIn("/api/settings", html)
        self.assertNotIn("mockSave('Settings saved in mock UI')", html)
        self.assertNotIn('type="text" value="UTC"', html)

    def test_profile_page_uses_real_profile_api_without_mock_save(self):
        html = PROFILE.read_text()
        self.assertIn('id="profileForm"', html)
        self.assertIn("/api/profile", html)
        self.assertIn("/api/auth/me", html)
        self.assertIn("/api/auth/verify-email", html)
        self.assertIn("/api/auth/resend-verification", html)
        self.assertNotIn("mockSave('Profile saved in Phase 1 mock UI')", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
