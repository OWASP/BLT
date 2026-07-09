import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "workers" / "main.py"
SRC = ROOT / "src"
CSS = SRC / "styles" / "sizzle-dashboard.css"


class TestCheckinDashboardContract(unittest.TestCase):
    def setUp(self):
        self.source = MAIN.read_text()
        self.normalized = re.sub(r"\s+", " ", self.source)

    def test_dashboard_metrics_route_is_registered(self):
        self.assertIn('"/api/dashboard" and method == "GET"', self.source)
        self.assertIn("handle_dashboard_metrics", self.source)

    def test_dashboard_page_is_session_gated_before_static_asset_fetch(self):
        static_start = self.source.index("# Static Pages & Assets")
        static_body = self.source[static_start:self.source.index("async def init_database")]
        self.assertIn("protected_pages", static_body)
        self.assertIn('"/dashboard": "/pages/dashboard.html"', static_body)
        self.assertIn('"/dashboard"', static_body[static_body.index("protected_pages"):])
        self.assertIn("await get_session_user(request, env)", static_body)
        self.assertIn('return redirect("/login")', static_body)
        session_check = static_body.index("await get_session_user(request, env)")
        asset_fetch = static_body.index("return await env.ASSETS.fetch(request_clone)")
        self.assertLess(session_check, asset_fetch)

    def test_page_directory_aliases_redirect_to_clean_routes(self):
        static_start = self.source.index("# Static Pages & Assets")
        static_body = self.source[static_start:self.source.index("async def init_database")]
        self.assertIn("canonical_page_routes", static_body)
        self.assertIn('"/pages/login": "/login"', static_body)
        self.assertIn('"/pages/login.html": "/login"', static_body)
        self.assertIn('"/pages/dashboard": "/dashboard"', static_body)
        self.assertIn('"/pages/dashboard.html": "/dashboard"', static_body)
        self.assertIn("if path in canonical_page_routes:", static_body)
        alias_check = static_body.index("if path in canonical_page_routes:")
        fallback_fetch = static_body.index("return await env.ASSETS.fetch(request)")
        self.assertLess(alias_check, fallback_fetch)

    def test_login_page_redirects_authenticated_sessions_to_dashboard_before_static_asset_fetch(self):
        static_start = self.source.index("# Static Pages & Assets")
        static_body = self.source[static_start:self.source.index("async def init_database")]
        page_route_body = static_body[
            static_body.index("elif path in page_assets:"):static_body.index('elif path == "/pages"')
        ]
        self.assertIn('return redirect("/dashboard")', page_route_body)
        combined_login_check = 'if path == "/login" and user_id:' in page_route_body
        split_login_check = 'if path == "/login":' in page_route_body and "if user_id:" in page_route_body
        self.assertTrue(combined_login_check or split_login_check)
        login_check = (
            page_route_body.index('if path == "/login" and user_id:')
            if combined_login_check
            else page_route_body.index('if path == "/login":')
        )
        dashboard_redirect = page_route_body.index('return redirect("/dashboard")')
        asset_fetch = page_route_body.index("return await env.ASSETS.fetch(request_clone)")
        self.assertLess(login_check, dashboard_redirect)
        self.assertLess(dashboard_redirect, asset_fetch)

    def test_checkin_routes_use_session_identity_and_approved_orgs(self):
        helper = self.source[self.source.index("async def get_approved_org_membership"):self.source.index("async def decrypt_checkin_row")]
        self.assertIn("get_verified_session_user", helper)
        for name in ["handle_checkin", "handle_get_all_checkins", "handle_get_latest_checkin"]:
            start = self.source.index(f"async def {name}")
            end = self.source.find("\n\nasync def ", start + 1)
            body = self.source[start:end if end != -1 else len(self.source)]
            self.assertIn("get_approved_org_membership", body, name)
            self.assertNotIn("data.get('userId')", body, name)
            self.assertNotIn("searchParams.get('userId')", body, name)

    def test_checkin_submission_updates_same_user_org_day_record(self):
        start = self.source.index("async def handle_checkin")
        end = self.source.index("async def handle_leaderboard")
        body = self.source[start:end]
        self.assertIn("checkin_date", body)
        self.assertIn("org_id", body)
        self.assertIn("UPDATE checkins", body)
        self.assertIn("INSERT INTO checkins", body)
        self.assertIn("d1_changes", body)
        self.assertIn('"created"', body)
        self.assertIn('"updated"', body)

    def test_checkin_responses_include_org_user_timezone_and_decrypted_fields(self):
        for name in ["handle_get_all_checkins", "handle_get_latest_checkin"]:
            start = self.source.index(f"async def {name}")
            end = self.source.find("\n\nasync def ", start + 1)
            body = self.source[start:end if end != -1 else len(self.source)] + self.source[self.source.index("def checkin_row_to_api"):self.source.index("async def handle_checkin")]
            for token in ["previousWork", "todayPlan", "blockers", "organization", "orgSlug", "checkinDate"]:
                self.assertIn(token, body, f"{name} should return {token}")
            helper = self.source[self.source.index("async def decrypt_checkin_row"):self.source.index("def checkin_row_to_api")]
            self.assertIn("decrypt_data", body + helper)

    def test_dashboard_metrics_are_role_aware_and_include_admin_queue(self):
        start = self.source.index("async def handle_dashboard_metrics")
        end = self.source.find("\n\nasync def ", start + 1)
        body = self.source[start:end if end != -1 else len(self.source)]
        for key in ["checkedInToday", "approvedMembers", "participationRate", "pendingRequests", "activeBlockers", "organizations", "activity", "adminQueue"]:
            self.assertIn(key, body)
        self.assertIn("('owner', 'admin')", body)
        self.assertIn("status = 'approved'", body)

    def test_frontend_pages_call_real_checkin_and_dashboard_apis(self):
        app = (SRC / "pages" / "app.html").read_text()
        history = (SRC / "pages" / "check-ins.html").read_text()
        dashboard = (SRC / "pages" / "dashboard.html").read_text()
        self.assertIn("/api/orgs", app)
        self.assertIn("/api/checkin/latest", app)
        self.assertIn("/api/checkin", app)
        self.assertIn("loadApprovedOrgs", app)
        self.assertIn("escapeHtml", app)
        self.assertNotIn("Phase 1 mock UI", app)
        self.assertIn("/api/checkins", history)
        self.assertIn("loadCheckins", history)
        self.assertIn("escapeHtml", history)
        self.assertNotIn("Finished login/signup flow", history)
        self.assertIn("/api/dashboard", dashboard)
        self.assertIn("loadDashboard", dashboard)
        self.assertIn("escapeHtml", dashboard)
        self.assertNotIn("Aisha", dashboard)

    def test_sidebar_menu_items_are_lighter_weight(self):
        css = CSS.read_text()
        self.assertIn(".sidebar-item {", css)
        self.assertIn("font-weight: 500;\n  line-height: 1.25;", css)
        self.assertNotIn("font-weight: 600;\n  line-height: 1.25;", css)


if __name__ == "__main__":
    unittest.main(verbosity=2)
