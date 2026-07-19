import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKERS = ROOT / "workers"
if str(WORKERS) not in sys.path:
    sys.path.insert(0, str(WORKERS))


class TestAuthFoundation(unittest.TestCase):
    def test_password_hash_round_trip_and_rejects_wrong_password(self):
        from auth_utils import hash_password, verify_password

        encoded = hash_password("correct horse battery staple", salt="00" * 16)

        self.assertTrue(encoded.startswith("pbkdf2_sha256$"))
        self.assertTrue(verify_password("correct horse battery staple", encoded))
        self.assertFalse(verify_password("wrong password", encoded))

    def test_session_cookie_is_httponly_samesite_and_clearable(self):
        from auth_utils import SESSION_COOKIE_NAME, build_clear_session_cookie, build_session_cookie

        cookie = build_session_cookie("abc123", 3600)
        insecure_cookie = build_session_cookie("abc123", 3600, secure=False)
        clear_cookie = build_clear_session_cookie()

        self.assertIn(f"{SESSION_COOKIE_NAME}=abc123", cookie)
        self.assertIn("Max-Age=3600", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        self.assertIn("Secure", cookie)
        self.assertNotIn("Secure", insecure_cookie)
        self.assertIn("Max-Age=0", clear_cookie)
        self.assertIn("Expires=Thu, 01 Jan 1970 00:00:00 GMT", clear_cookie)
        self.assertIn("Secure", clear_cookie)

    def test_session_hash_requires_secret_and_is_stable(self):
        from auth_utils import session_hash

        self.assertEqual(session_hash("token", "secret"), session_hash("token", "secret"))
        self.assertNotEqual(session_hash("token", "secret"), session_hash("other", "secret"))
        with self.assertRaises(ValueError):
            session_hash("token", "")

    def test_otp_generation_and_verification(self):
        from auth_utils import generate_otp, hash_otp, verify_otp

        otp = generate_otp()
        digest = hash_otp("user@example.com", otp, "login", "otp-secret")

        self.assertRegex(otp, r"^\d{6}$")
        self.assertTrue(verify_otp("user@example.com", otp, "login", "otp-secret", digest))
        self.assertTrue(verify_otp("USER@example.com", otp, "login", "otp-secret", digest))
        self.assertFalse(verify_otp("user@example.com", "000000", "login", "otp-secret", digest))
        self.assertFalse(verify_otp("other@example.com", otp, "login", "otp-secret", digest))


class TestEmailFoundation(unittest.TestCase):
    def test_sendgrid_payload_has_expected_shape_and_custom_args(self):
        from email_service import build_sendgrid_payload

        payload = build_sendgrid_payload(
            to_email="member@example.com",
            subject="Your Sizzle verification code",
            html_content="<p>123456</p>",
            from_email="noreply@owaspblt.org",
            from_name="BLT Sizzle",
            custom_args={"purpose": "login_otp"},
        )

        self.assertEqual(payload["personalizations"][0]["to"][0]["email"], "member@example.com")
        self.assertEqual(payload["from"], {"email": "noreply@owaspblt.org", "name": "BLT Sizzle"})
        self.assertEqual(payload["subject"], "Your Sizzle verification code")
        self.assertEqual(payload["content"], [{"type": "text/html", "value": "<p>123456</p>"}])
        self.assertEqual(payload["custom_args"], {"purpose": "login_otp"})
        json.dumps(payload)

    def test_email_service_reports_unconfigured_without_network(self):
        from email_service import SendGridEmailService

        async def run():
            service = SendGridEmailService(api_key="", from_email="")
            return await service.send_email("member@example.com", "Subject", "<p>Body</p>")

        import asyncio
        result = asyncio.run(run())

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], 503)
        self.assertEqual(result["provider"], "sendgrid")
        self.assertTrue(result["permanent_failure"])

    def test_render_otp_email_contains_code_and_escapes_email(self):
        from email_service import render_otp_email

        html = render_otp_email("User <bad>@example.com", "123456")

        self.assertIn("123456", html)
        self.assertIn("BLT Sizzle", html)
        self.assertNotIn("User <bad>", html)
        self.assertIn("&lt;bad&gt;", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
