import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
MAIN = ROOT / "workers" / "main.py"


class TestAppRefactorFrontendContracts(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text()

    def test_home_route_is_public_landing_not_checkin_form(self):
        html = self.read("src/index.html")
        self.assertIn("Sizzle", html)
        self.assertIn("Daily check-ins", html)
        self.assertIn("dot-field", html)
        self.assertIn("#dc2626", html)
        self.assertIn("href=\"/login\"", html)
        self.assertNotIn("id=\"checkinForm\"", html)
        self.assertNotIn("Login with GitHub", html)

    def test_login_page_uses_email_otp_endpoints_and_design_tokens(self):
        html = self.read("src/pages/login.html")
        self.assertIn("id=\"emailForm\"", html)
        self.assertIn("id=\"otpForm\"", html)
        self.assertIn("/api/auth/request-otp", html)
        self.assertIn("/api/auth/verify-otp", html)
        self.assertIn("#dc2626", html)
        self.assertIn("BLT Sizzle", html)
        self.assertNotIn("GitHub", html)

    def test_app_page_keeps_checkin_form_but_uses_email_login_and_approved_orgs(self):
        html = self.read("src/pages/app.html")
        self.assertIn("id=\"checkinForm\"", html)
        self.assertIn("id=\"orgSelector\"", html)
        self.assertIn("/login", html)
        self.assertIn("status === 'approved'", html)
        self.assertIn("const approvedOrgs", html)
        self.assertIn("approvedOrgs.length > 0", html)
        self.assertIn('href="/app" class="text-primary font-bold"', html)
        self.assertIn("#dc2626", html)
        self.assertNotIn("Login with GitHub", html)
        self.assertNotIn("api/auth/login", html)

    def test_worker_routes_login_and_app_pages(self):
        source = MAIN.read_text()
        self.assertIn('"/login"', source)
        self.assertIn('"/app"', source)
        self.assertIn('/pages/login.html', source)
        self.assertIn('/pages/app.html', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
