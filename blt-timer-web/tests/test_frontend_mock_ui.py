from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "public" / "index.html"
LOGIN = ROOT / "public" / "login.html"
DASHBOARD = ROOT / "public" / "dashboard.html"
APP_JS = ROOT / "public" / "app.js"
AUTH_JS = ROOT / "public" / "auth.js"
DASHBOARD_JS = ROOT / "public" / "dashboard.js"
STYLES = ROOT / "public" / "styles.css"
LOGS = ROOT / "public" / "logs.html"
HISTORY = ROOT / "public" / "history.html"
SETTINGS = ROOT / "public" / "settings.html"
SHARED_DASHBOARD_JS = ROOT / "public" / "dashboard-shared.js"
TIMER_PAGE_JS = ROOT / "public" / "timer-page.js"
LOGS_PAGE_JS = ROOT / "public" / "logs-page.js"
HISTORY_PAGE_JS = ROOT / "public" / "history-page.js"
SETTINGS_PAGE_JS = ROOT / "public" / "settings-page.js"


class FrontendProductionUITests(unittest.TestCase):
    def test_landing_page_is_real_marketing_page_not_mock_dashboard(self):
        html = INDEX.read_text()

        for expected in [
            "https://cdn.tailwindcss.com",
            "BLT Timer",
            "Start. Work. Save. Done.",
            "A minimal time tracker for BLT contributors.",
            "No screenshots. No keystroke tracking. No provider OAuth. Just simple work logs.",
            'id="how-it-works"',
            'id="features"',
            'id="privacy"',
            'id="final-cta"',
            'href="/login"',
            'href="/dashboard"',
        ]:
            self.assertIn(expected, html)

        self.assertNotIn("Mock dashboard", html)
        self.assertNotIn("Custom auth mock", html)
        self.assertNotIn("Mock UI for review", html)

    def test_login_page_contains_real_auth_forms_and_api_script(self):
        html = LOGIN.read_text()
        js = AUTH_JS.read_text()

        for expected in [
            "Welcome back",
            "Create account",
            'id="login-form"',
            'id="register-form"',
            'src="/auth.js"',
        ]:
            self.assertIn(expected, html)

        for expected in [
            "/api/auth/login",
            "/api/auth/register",
            "credentials: 'include'",
            "window.location.href = '/dashboard'",
        ]:
            self.assertIn(expected, js)

        self.assertNotIn("GitHub", html)
        self.assertNotIn("GitLab", html)

    def test_timer_page_is_authenticated_timer_app(self):
        html = DASHBOARD.read_text()
        js = TIMER_PAGE_JS.read_text() + SHARED_DASHBOARD_JS.read_text()

        for expected in [
            "Timer | BLT Timer",
            'data-dashboard-page="timer"',
            'id="dashboard-root"',
            'src="/timer-page.js"',
        ]:
            self.assertIn(expected, html)

        for expected in [
            "/api/me",
            "/api/logs",
            "/api/stats?range=week",
            "/api/auth/logout",
            "credentials: 'include'",
            "localStorage",
            "startTimer",
            "clearTimer()",
            "createLogModal",
        ]:
            self.assertIn(expected, js)

    def test_logs_and_history_pages_have_log_management_controls(self):
        logs_html = LOGS.read_text()
        history_html = HISTORY.read_text()
        js = LOGS_PAGE_JS.read_text() + HISTORY_PAGE_JS.read_text()

        for expected in [
            'data-dashboard-page="logs"',
            'src="/logs-page.js"',
        ]:
            self.assertIn(expected, logs_html)

        for expected in [
            'data-dashboard-page="history"',
            'src="/history-page.js"',
        ]:
            self.assertIn(expected, history_html)

        for expected in [
            "openForEdit",
            "deleteLog",
            "method: 'PATCH'",
            "method: 'DELETE'",
            "URLSearchParams",
            "range-filter",
            "data-action=\"edit-log\"",
            "data-action=\"delete-log\"",
            "window.confirm('Delete this work log? This cannot be undone.')",
        ]:
            self.assertIn(expected, js)

    def test_settings_uses_a_complete_timezone_dropdown(self):
        settings = SETTINGS_PAGE_JS.read_text()
        timezone_module = ROOT / "public" / "timezones.js"
        auth = AUTH_JS.read_text()

        self.assertTrue(timezone_module.exists())
        timezones = timezone_module.read_text()
        self.assertIn('<select id="timezone"', settings)
        self.assertNotIn('<input id="timezone"', settings)
        self.assertIn("populateTimezoneSelect", settings)
        self.assertIn("Intl.supportedValuesOf('timeZone')", timezones)
        self.assertIn("UTC", timezones)
        self.assertIn("detectTimezone", auth)
        self.assertIn("timezone: detectTimezone()", auth)

    def test_dashboard_has_focused_pages_with_shared_navigation(self):
        pages = {
            DASHBOARD: ("timer", "Timer | BLT Timer", "timer-page.js"),
            LOGS: ("logs", "Recent logs | BLT Timer", "logs-page.js"),
            HISTORY: ("history", "History | BLT Timer", "history-page.js"),
            SETTINGS: ("settings", "Settings | BLT Timer", "settings-page.js"),
        }

        for path, (page_id, title, script) in pages.items():
            html = path.read_text()
            self.assertIn(f'data-dashboard-page="{page_id}"', html, path)
            self.assertIn('id="dashboard-root"', html, path)
            self.assertIn(f"<title>{title}</title>", html, path)
            self.assertIn(f'src="/{script}"', html, path)

        shared = SHARED_DASHBOARD_JS.read_text()
        for href in ["/dashboard", "/logs", "/history", "/settings"]:
            self.assertIn(href, shared)
        self.assertIn("sidebar-item", shared)
        self.assertIn("pageId === id", shared)
        self.assertIn("/api/me", shared)
        self.assertIn("window.location.href = '/login'", shared)

    def test_dashboard_shell_uses_the_blt_logo_without_redundant_header_content(self):
        shared = SHARED_DASHBOARD_JS.read_text()

        self.assertIn('src="/assets/logo.png"', shared)
        self.assertNotIn('<span aria-hidden="true">⌂</span><span>Home</span>', shared)
        self.assertNotIn('<p class="section-kicker">BLT Timer</p>', shared)
        self.assertNotIn('<p>${subtitle}</p>', shared)
        self.assertNotIn('BLT Contributor', shared)

    def test_dashboard_shared_module_preserves_active_timer_across_pages(self):
        shared = SHARED_DASHBOARD_JS.read_text()
        timer_page = TIMER_PAGE_JS.read_text()

        self.assertIn("const TIMER_KEY = 'blt_timer_active_session'", shared)
        self.assertIn("localStorage.getItem(TIMER_KEY)", shared)
        self.assertIn("localStorage.removeItem(TIMER_KEY)", shared)
        self.assertIn("clearTimer()", timer_page)
        self.assertIn("title: document.querySelector('#task-title').value.trim()", timer_page)
        self.assertIn("timer.title || ''", timer_page)

    def test_pages_link_local_assets_and_avoid_gradients(self):
        html = INDEX.read_text() + LOGIN.read_text() + DASHBOARD.read_text()
        styles = STYLES.read_text()

        self.assertIn('href="/styles.css"', html)
        self.assertIn("--primary: #dc2626", styles)
        self.assertNotIn("linear-gradient", html)
        self.assertNotIn("linear-gradient", styles)
        self.assertNotIn("radial-gradient", html)
        self.assertNotIn("radial-gradient", styles)
        self.assertNotIn("bg-gradient", html)

    def test_landing_footer_shows_timer_domain_and_contribution_link(self):
        html = INDEX.read_text()

        self.assertIn("footer-panel", html)
        self.assertIn('aria-label="Footer navigation"', html)
        self.assertIn("timer.owaspblt.org", html)
        self.assertIn('href="https://gitlab.com/owasp-blt/blt-timer-web"', html)
        self.assertIn("GitLab repo", html)
        self.assertIn('href="https://gitlab.com/owasp-blt"', html)
        self.assertIn("BLT TIMER", html)
        self.assertIn("Start timer", html)


if __name__ == "__main__":
    unittest.main()
