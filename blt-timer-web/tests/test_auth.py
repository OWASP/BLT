import importlib
import re
import unittest


class AuthHelperTests(unittest.TestCase):
    def load_auth(self):
        return importlib.import_module("src.auth")

    def test_password_hash_verifies_correct_password_and_rejects_wrong_password(self):
        auth = self.load_auth()

        stored_hash = auth.hash_password("correct horse battery staple")

        self.assertRegex(
            stored_hash,
            r"^pbkdf2_sha256\$[0-9]+\$[0-9a-f]+\$[0-9a-f]+$",
        )
        self.assertTrue(auth.verify_password("correct horse battery staple", stored_hash))
        self.assertFalse(auth.verify_password("wrong password", stored_hash))
        self.assertFalse(auth.verify_password("correct horse battery staple", "invalid"))

    def test_session_hash_and_token_are_high_entropy_safe_values(self):
        auth = self.load_auth()

        first_token = auth.generate_session_token()
        second_token = auth.generate_session_token()
        token_hash = auth.session_hash(first_token, "development-secret")

        self.assertNotEqual(first_token, second_token)
        self.assertGreaterEqual(len(first_token), 43)
        self.assertRegex(token_hash, r"^[0-9a-f]{64}$")
        self.assertNotEqual(token_hash, first_token)

    def test_session_cookie_includes_http_only_lax_and_path(self):
        auth = self.load_auth()

        cookie = auth.build_session_cookie("token-value", 3600)

        self.assertIn("blt_timer_session=token-value", cookie)
        self.assertIn("Max-Age=3600", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        self.assertIn("Path=/", cookie)
        self.assertNotIn("Secure", cookie)

    def test_secure_session_cookie_can_be_requested_for_production(self):
        auth = self.load_auth()

        cookie = auth.build_session_cookie("token-value", 3600, secure=True)

        self.assertIn("Secure", cookie)

    def test_clear_session_cookie_expires_cookie(self):
        auth = self.load_auth()

        cookie = auth.build_clear_session_cookie()

        self.assertIn("blt_timer_session=", cookie)
        self.assertIn("Max-Age=0", cookie)
        self.assertIn("Expires=Thu, 01 Jan 1970 00:00:00 GMT", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        self.assertIn("Path=/", cookie)

    def test_parse_cookie_returns_cookie_values(self):
        auth = self.load_auth()

        parsed = auth.parse_cookie("theme=light; blt_timer_session=abc123; other=value")

        self.assertEqual(parsed["theme"], "light")
        self.assertEqual(parsed["blt_timer_session"], "abc123")

    def test_normalize_email_and_username(self):
        auth = self.load_auth()

        self.assertEqual(auth.normalize_email(" USER@Example.COM "), "user@example.com")
        self.assertEqual(auth.normalize_username(" Md-Kaif_04 "), "md-kaif_04")

        with self.assertRaises(ValueError):
            auth.normalize_email("not-an-email")
        with self.assertRaises(ValueError):
            auth.normalize_username("ab")
        with self.assertRaises(ValueError):
            auth.normalize_username("bad username")


if __name__ == "__main__":
    unittest.main()
