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
        legacy_login = self.source.index('"/api/auth/login" and method == "GET"')
        self.assertLess(request_otp, legacy_login)
        self.assertLess(verify_otp, legacy_login)
        self.assertIn("handle_auth_request_otp", self.source)
        self.assertIn("handle_auth_verify_otp", self.source)

    def test_main_imports_shared_auth_and_email_foundation(self):
        for name in [
            "hash_password",
            "verify_password",
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

    def test_json_response_converts_response_init_to_javascript_object(self):
        start = self.source.index("def json_response")
        end = self.source.index("def json_error")
        body = self.source[start:end]
        self.assertIn("to_js({", body)
        self.assertIn("dict_converter=Object.fromEntries", body)
        self.assertIn('"status": status', body)
        self.assertIn('"headers": headers', body)

    def test_auth_me_uses_json_response_status_helper(self):
        start = self.source.index("async def handle_auth_me")
        end = self.source.index("async def handle_auth_logout")
        body = self.source[start:end]
        self.assertIn('return json_response({"authenticated": False}, 401)', body)
        self.assertIn('return json_response({"authenticated": False}, 500)', body)
        self.assertNotIn('{"status": 401, "headers"', body)

    def test_signup_login_and_email_verification_routes_are_registered(self):
        signup = self.source.index('"/api/auth/signup"')
        credential_login = self.source.index('"/api/auth/login" and method == "POST"')
        verify_email = self.source.index('"/api/auth/verify-email"')
        resend = self.source.index('"/api/auth/resend-verification"')
        legacy_get_login = self.source.index('"/api/auth/login" and method == "GET"')
        self.assertLess(signup, legacy_get_login)
        self.assertLess(credential_login, legacy_get_login)
        self.assertLess(verify_email, legacy_get_login)
        self.assertLess(resend, legacy_get_login)
        for handler in [
            "handle_auth_signup",
            "handle_auth_password_login",
            "handle_auth_verify_email",
            "handle_auth_resend_verification",
        ]:
            self.assertIn(handler, self.source)

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
        self.assertIn("OTP email config", body)
        self.assertIn("OTP email send result", body)
        self.assertIn("OTP email send failed", body)
        self.assertIn("provider_message_id", body)
        self.assertIn("recipient_domain", body)
        self.assertNotIn("devOtp", body)
        self.assertNotIn('"otp"', body.split("return Response.new")[-1])

    def test_email_config_supports_current_and_legacy_sendgrid_env_names(self):
        self.assertIn("def get_email_config", self.source)
        self.assertIn('"EMAIL_API_KEY", "SENDGRID_API_KEY"', self.source)
        self.assertIn('"EMAIL_FROM", "SENDGRID_FROM_EMAIL"', self.source)
        self.assertIn('"EMAIL_FROM_NAME", "SENDGRID_FROM_NAME"', self.source)
        self.assertIn("Email service provider is not supported", self.source)

    def test_auth_routes_do_not_use_hardcoded_secret_fallbacks(self):
        self.assertNotIn("sizzle-dev-otp-secret", self.source)
        self.assertNotIn("sizzle-dev-session-secret", self.source)

    def test_signup_creates_unverified_password_user_and_sends_verification_code(self):
        start = self.source.index("async def handle_auth_signup")
        end = self.source.index("async def handle_auth_password_login")
        body = self.source[start:end]
        self.assertIn("displayName", body)
        self.assertIn("hash_password", body)
        self.assertIn("password_hash", body)
        self.assertIn("email_verified, status", body)
        self.assertIn("0, 'active'", body)
        self.assertIn("send_email_verification_code", body)
        self.assertIn('"needsEmailVerification": True', body)
        self.assertIn('"success": True', body)
        self.assertNotIn('"Set-Cookie"', body)
        self.assertNotIn('"password"', body.split("return json_response")[-1])

    def test_password_login_verifies_credentials_and_never_logs_passwords(self):
        start = self.source.index("async def handle_auth_password_login")
        end = self.source.index("async def handle_auth_verify_email")
        body = self.source[start:end]
        self.assertIn("verify_password", body)
        self.assertIn("password_hash", body)
        self.assertIn("status = 'active'", body)
        self.assertIn("send_email_verification_code", body)
        self.assertIn('"authenticated": False', body)
        self.assertIn("build_session_cookie", body)
        self.assertIn("Invalid email or password", body)
        self.assertIn("auth_login_attempts", body)
        self.assertIn("datetime('now', '-15 minutes')", body)
        self.assertIn("Too many login attempts", body)
        self.assertIn('"emailVerified"', body)
        self.assertNotIn("logger.info(\"%s", body)

    def test_verify_email_consumes_email_verify_otp_and_marks_user_verified(self):
        start = self.source.index("async def handle_auth_verify_email")
        end = self.source.index("async def handle_auth_resend_verification")
        body = self.source[start:end]
        self.assertIn("purpose = 'email_verify'", body)
        self.assertIn("verify_otp", body)
        self.assertIn("UPDATE email_otps", body)
        self.assertIn("consumed_at IS NULL", body)
        self.assertIn("UPDATE users SET email_verified = 1", body)
        self.assertIn("d1_changes", body)

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
