import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
MAIN = ROOT / "workers" / "main.py"
WRANGLER = ROOT / "wrangler.toml"
CONTRIBUTION_URL = "https://gitlab.com/owasp-blt/blt-sizzle"
LEGACY_CONTRIBUTION_URL = "https://github.com/OWASP-BLT/BLT-Sizzle"


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

    def test_landing_header_uses_public_logo_asset(self):
        html = self.read("src/index.html")
        self.assertIn('src="/assets/logo.png"', html)
        self.assertNotIn("/assets/images/owasp-blt-logo.svg", html)
        self.assertTrue((SRC / "assets" / "logo.png").is_file())

    def test_landing_footer_has_sizzle_domain_and_link_groups(self):
        html = self.read("src/index.html")
        footer = html[html.index("<footer"):]
        self.assertIn("sizzle.owaspblt.org", footer)
        self.assertIn(CONTRIBUTION_URL, footer)
        self.assertNotIn(LEGACY_CONTRIBUTION_URL, footer)
        for label in ("DOCS", "SIZZLE", "PROJECT", "OWASP"):
            self.assertIn(label, footer)
        for link in (
            "Dashboard",
            "Health",
            "Check in",
            "Settings",
            "Leaderboard",
            "GitLab repo",
            "OWASP BLT group",
            "OWASP BLT",
            "Foundation page",
            "owasp.org",
        ):
            self.assertIn(link, footer)

    def test_app_pages_use_gitlab_contribution_url(self):
        for page in SRC.rglob("*.html"):
            html = page.read_text()
            self.assertNotIn(LEGACY_CONTRIBUTION_URL, html, str(page))
        for page in ("src/index.html", "src/pages/app.html"):
            self.assertIn(CONTRIBUTION_URL, self.read(page), page)
        app_html = self.read("src/pages/app.html")
        self.assertIn('title="View on GitLab"', app_html)
        self.assertNotIn("View on GitHub", app_html)

    def test_login_page_uses_email_otp_endpoints_and_design_tokens(self):
        html = self.read("src/pages/login.html")
        self.assertIn("id=\"loginForm\"", html)
        self.assertIn("id=\"signupForm\"", html)
        self.assertIn("id=\"verifyEmailForm\"", html)
        self.assertIn("id=\"emailForm\"", html)
        self.assertIn("id=\"otpForm\"", html)
        self.assertIn("name=\"displayName\"", html)
        self.assertIn("type=\"password\"", html)
        self.assertIn("/api/auth/signup", html)
        self.assertIn("/api/auth/login", html)
        self.assertIn("/api/auth/verify-email", html)
        self.assertIn("/api/auth/resend-verification", html)
        self.assertIn("/api/auth/request-otp", html)
        self.assertIn("/api/auth/verify-otp", html)
        self.assertIn("#dc2626", html)
        self.assertIn("BLT Sizzle", html)
        self.assertIn('src="/assets/logo.png"', html)
        self.assertNotIn("/assets/images/owasp-blt-logo.svg", html)
        self.assertIn("setPending", html)
        self.assertIn("Network error while requesting the verification code", html)
        self.assertIn("Network error while verifying the code", html)
        self.assertIn("finally", html)
        self.assertIn("Create account", html)
        self.assertIn("Verify email", html)
        self.assertIn("Email verified. You can now log in.", html)
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
        self.assertIn("/styles/sizzle-dashboard.css", html)
        self.assertNotIn("Login with GitHub", html)
        self.assertNotIn("api/auth/login", html)

    def test_secondary_pages_link_to_email_login_not_legacy_github_oauth(self):
        for page in ["src/pages/settings.html", "src/pages/check-ins.html", "src/pages/leaderboard.html"]:
            html = self.read(page)
            self.assertIn("/login", html, page)
            self.assertNotIn('href="/api/auth/login"', html, page)
            self.assertNotIn("Login with GitHub", html, page)

    def test_phase_one_dashboard_shell_assets_exist(self):
        css = self.read("src/styles/sizzle-dashboard.css")
        js = self.read("src/scripts/sizzle-ui.js")
        self.assertIn("--primary: #dc2626", css)
        self.assertIn(".sizzle-shell", css)
        self.assertIn(".sidebar-item.active", css)
        self.assertIn("showToast", js)
        self.assertIn("openSheet", js)
        self.assertIn("openModal", js)
        self.assertNotIn("mock", js.lower())

    def test_dashboard_shell_uses_clean_newsletter_inspired_style(self):
        css = self.read("src/styles/sizzle-dashboard.css")
        self.assertIn("--radius: 8px", css)
        self.assertIn("--nav-icon", css)
        self.assertIn("box-shadow: none", css)
        self.assertIn(".main-panel > .page-header", css)
        self.assertIn("background: linear-gradient(to bottom, #ef4444, #dc2626)", css)
        self.assertIn("border-bottom-color: #991b1b", css)
        self.assertIn(".sidebar-item.active { color: var(--primary); background: transparent; }", css)
        self.assertIn(".sidebar-item.active::after", css)
        self.assertNotIn("0 18px 50px", css)
        self.assertNotIn("border-radius: 16px", css)

    def test_dashboard_controls_use_small_variant_sizing(self):
        css = self.read("src/styles/sizzle-dashboard.css")
        self.assertIn("min-height: 34px;", css)
        self.assertIn("padding: 7px 11px;", css)
        self.assertIn("font-size: 13px;", css)
        self.assertIn("padding: 8px 10px;", css)
        self.assertIn("min-height: 92px;", css)
        self.assertNotIn("min-height: 40px;", css)
        self.assertNotIn("padding: 10px 14px;", css)
        self.assertNotIn("padding: 12px 13px;", css)

    def test_auth_page_uses_professional_copy_and_small_controls(self):
        html = self.read("src/pages/login.html")
        self.assertIn("Welcome to Sizzle", html)
        self.assertIn("Create your account or log in to manage daily check-ins", html)
        self.assertIn("auth-control-sm", html)
        self.assertIn("auth-input-sm", html)
        self.assertIn("auth-button-sm", html)
        self.assertIn("overflow-x-hidden", html)
        self.assertNotIn("180vw", html)
        self.assertNotIn("Credentials + email verification", html)
        self.assertNotIn("Sign up once. Log in with credentials.", html)
        self.assertNotIn("First-time users create an account", html)
        self.assertNotIn("Log in later with credentials", html)
        self.assertNotIn("Passwordless OTP login is being kept temporarily for migration.", html)

    def test_dashboard_typography_keeps_navigation_and_metrics_normal_weight(self):
        css = self.read("src/styles/sizzle-dashboard.css")
        self.assertIn(".brand strong {\n  display: block;\n  color: var(--ink);\n  font-size: 15px;\n  line-height: 1.25;\n  font-weight: 600;", css)
        self.assertIn(".sidebar-item {\n  --nav-icon", css)
        self.assertIn("font-weight: 500;\n  line-height: 1.25;", css)
        self.assertNotIn("font-weight: 600;\n  line-height: 1.25;", css)
        self.assertIn(".sidebar-footer a {\n  display: inline-flex;", css)
        self.assertIn(".metric-value {\n  margin-top: 12px;\n  font-size: 36px;\n  line-height: 1;\n  letter-spacing: 0;\n  font-weight: 600;", css)
        self.assertNotIn("font-weight: 850", css)
        self.assertNotIn("font-weight: 750", css)

    def test_phase_one_pages_use_clean_sidebar_shell(self):
        required_nav = ["Overview", "Daily Check-in", "Organizations", "Check-ins", "Profile", "Settings"]
        removed_nav_links = ['href="/organizations#requests"', 'href="/organizations#members"']
        for page in [
            "src/pages/dashboard.html",
            "src/pages/app.html",
            "src/pages/organizations.html",
            "src/pages/profile.html",
            "src/pages/check-ins.html",
            "src/pages/settings.html",
            "src/pages/leaderboard.html",
        ]:
            html = self.read(page)
            nav = html[html.index("<nav class=\"sidebar-nav\""):html.index("</nav>")]
            self.assertIn("sizzle-shell", html, page)
            self.assertIn("sizzle-sidebar", html, page)
            self.assertIn("/styles/sizzle-dashboard.css", html, page)
            self.assertIn("/scripts/sizzle-ui.js", html, page)
            for label in required_nav:
                self.assertIn(label, nav, page)
            for link in removed_nav_links:
                self.assertNotIn(link, nav, page)
            self.assertNotIn("Login with GitHub", html, page)
            self.assertNotIn('href="/api/auth/login"', html, page)

    def test_app_pages_do_not_show_internal_phase_or_inspiration_labels(self):
        internal_labels = ["BLT-Newsletter-inspired", "Phase 1", "Phase 2", "Phase 2A", "Phase 2B", "Phase 2C"]
        for page in [
            "src/pages/dashboard.html",
            "src/pages/app.html",
            "src/pages/organizations.html",
            "src/pages/profile.html",
            "src/pages/check-ins.html",
            "src/pages/settings.html",
            "src/pages/leaderboard.html",
        ]:
            html = self.read(page)
            for label in internal_labels:
                self.assertNotIn(label, html, page)

    def test_shared_assets_do_not_keep_removed_nav_or_mock_phase_copy(self):
        css = self.read("src/styles/sizzle-dashboard.css")
        js = self.read("src/scripts/sizzle-ui.js")
        self.assertNotIn('/organizations#requests', css)
        self.assertNotIn('/organizations#members', css)
        self.assertNotIn("Phase 1 mock UI", js)

    def test_profile_page_contains_email_verification_flow(self):
        html = self.read("src/pages/profile.html")
        self.assertIn("Verify email", html)
        self.assertIn("Resend verification code", html)
        self.assertIn("/api/auth/verify-email", html)
        self.assertIn("/api/auth/resend-verification", html)
        self.assertIn("verification-status", html)

    def test_organizations_page_contains_create_join_and_role_management_ui(self):
        html = self.read("src/pages/organizations.html")
        for text in ["Create organization", "Request to join", "Membership status", "owner", "admin", "member"]:
            self.assertIn(text, html)
        self.assertIn("organizationSheet", html)
        self.assertIn("createOrgModal", html)
        self.assertIn("/api/orgs/discover", html)
        self.assertIn("/api/orgs/${slug}/join", html)
        self.assertIn("/api/orgs", html)
        self.assertIn("loadOrganizations", html)
        self.assertIn("escapeHtml", html)
        self.assertNotIn("Phase 1 mock UI", html)

    def test_worker_routes_phase_one_pages(self):
        source = MAIN.read_text()
        for route in ['"/login"', '"/app"', '"/dashboard"', '"/profile"', '"/organizations"']:
            self.assertIn(route, source)
        for page in ['/pages/login.html', '/pages/app.html', '/pages/dashboard.html', '/pages/profile.html', '/pages/organizations.html']:
            self.assertIn(page, source)

    def test_worker_serves_home_route_from_index_asset(self):
        source = MAIN.read_text()
        root_route = 'if path == "" or path == "/" or path == "/index.html":'
        self.assertIn(root_route, source)
        root_body = source[source.index(root_route):source.index('elif path in page_assets:')]
        self.assertIn('url_clone.pathname = "/index.html"', root_body)
        self.assertIn("request_clone = Request.new(url_clone, request)", root_body)
        self.assertIn("return await env.ASSETS.fetch(request_clone)", root_body)

    def test_wrangler_routes_page_assets_through_worker_without_html_redirects(self):
        config = WRANGLER.read_text()
        self.assertIn('html_handling = "none"', config)
        self.assertIn("run_worker_first = [", config)
        for route in ['"/"', '"/index.html"', '"/login"', '"/dashboard"', '"/app"', '"/profile"', '"/organizations"', '"/pages"', '"/pages/*"']:
            self.assertIn(route, config)


if __name__ == "__main__":
    unittest.main(verbosity=2)
