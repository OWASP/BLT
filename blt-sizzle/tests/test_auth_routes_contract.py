import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "workers" / "main.py"


class TestOtpAuthRouteContract(unittest.TestCase):
    def setUp(self):
        self.source = MAIN.read_text()
        self.normalized = re.sub(r"\s+", " ", self.source)

    def test_email_otp_routes_are_registered_before_legacy_github_login(self):
        request_otp = self.source.index('"/api/auth/request-otp"')
        verify_otp = self.source.index('"/api/auth/verify-otp"')
        legacy_login = self.source.index('"/api/auth/login"')
        self.assertLess(request_otp, legacy_login)
        self.assertLess(verify_otp, legacy_login)
        self.assertIn("handle_auth_request_otp", self.source)
        self.assertIn("handle_auth_verify_otp", self.source)

    def test_main_imports_shared_auth_and_email_foundation(self):
        for name in [
            "generate_otp",
            "hash_otp",
            "verify_otp",
            "generate_session_token",
            "session_hash",
            "build_session_cookie",
            "build_clear_session_cookie",
            "normalize_email",
            "SendGridEmailService",
            "render_otp_email",
        ]:
            self.assertIn(name, self.source)

    def test_init_database_creates_email_otp_and_auth_session_tables(self):
        self.assertIn("CREATE TABLE IF NOT EXISTS auth_sessions", self.source)
        self.assertIn("CREATE TABLE IF NOT EXISTS email_otps", self.source)
        self.assertIn("idx_auth_sessions_hash", self.source)
        self.assertIn("idx_email_otps_email_purpose", self.source)

    def test_get_session_user_checks_hashed_auth_sessions_before_legacy_sessions(self):
        auth_session_pos = self.source.index("FROM auth_sessions")
        legacy_session_pos = self.source.index("FROM sessions")
        self.assertLess(auth_session_pos, legacy_session_pos)
        self.assertIn("session_hash(session_token", self.source)

    def test_request_otp_uses_sendgrid_service_and_never_returns_otp(self):
        start = self.source.index("async def handle_auth_request_otp")
        end = self.source.index("async def handle_auth_verify_otp")
        body = self.source[start:end]
        self.assertIn("SendGridEmailService", body)
        self.assertIn("render_otp_email", body)
        self.assertIn("hash_otp", body)
        self.assertIn("INSERT INTO email_otps", body)
        self.assertIn("COUNT(*) AS recent_count", body)
        self.assertIn("datetime('now', '-1 hour')", body)
        self.assertLess(body.index("INSERT INTO email_otps"), body.index("service.send_email"))
        self.assertIn("UPDATE email_otps", body)
        self.assertIn("SET consumed_at = CURRENT_TIMESTAMP", body)
        self.assertNotIn("DELETE FROM email_otps\n            WHERE email = ?", body)
        self.assertIn("DELETE FROM email_otps WHERE id = ?", body)
        self.assertNotIn("devOtp", body)
        self.assertNotIn('"otp"', body.split("return Response.new")[-1])

    def test_auth_routes_do_not_use_hardcoded_secret_fallbacks(self):
        self.assertNotIn("sizzle-dev-otp-secret", self.source)
        self.assertNotIn("sizzle-dev-session-secret", self.source)

    def test_verify_otp_consumes_otp_and_sets_session_cookie(self):
        start = self.source.index("async def handle_auth_verify_otp")
        end = self.source.index("async def handle_auth_me")
        body = self.source[start:end]
        self.assertIn("verify_otp", body)
        self.assertIn("UPDATE email_otps", body)
        self.assertIn("consumed_at IS NULL", body)
        self.assertIn("changes", body)
        self.assertIn("INSERT INTO auth_sessions", body)
        self.assertIn("build_session_cookie", body)
        self.assertIn('"Set-Cookie"', body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
