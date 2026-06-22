import asyncio
import importlib
import inspect
import json
import os
import re
import sqlite3
import subprocess
import sys
import types
import unittest
from unittest import mock
from pathlib import Path

from src.newsletter_validation import email_hash


ROOT = Path(__file__).resolve().parents[1]


class AdminAuthHelperTests(unittest.TestCase):
    def load_admin_auth(self):
        module_path = ROOT / "src" / "admin_auth.py"
        if not module_path.exists():
            self.fail("src/admin_auth.py must provide import-safe admin auth helpers")

        return importlib.import_module("src.admin_auth")

    def test_password_hash_verifies_correct_password_and_rejects_wrong_password(self):
        admin_auth = self.load_admin_auth()

        stored_hash = admin_auth.hash_password("correct horse battery staple")

        self.assertRegex(
            stored_hash,
            r"^pbkdf2_sha256\$[0-9]+\$[0-9a-f]+\$[0-9a-f]+$",
        )
        self.assertTrue(
            admin_auth.verify_password("correct horse battery staple", stored_hash)
        )
        self.assertFalse(admin_auth.verify_password("wrong password", stored_hash))

    def test_session_hash_and_token_are_high_entropy_safe_values(self):
        admin_auth = self.load_admin_auth()

        first_token = admin_auth.generate_session_token()
        second_token = admin_auth.generate_session_token()
        token_hash = admin_auth.session_hash(first_token, "session-secret")

        self.assertNotEqual(first_token, second_token)
        self.assertGreaterEqual(len(first_token), 43)
        self.assertRegex(token_hash, r"^[0-9a-f]{64}$")
        self.assertNotEqual(token_hash, first_token)

    def test_session_cookie_includes_http_only_lax_and_path(self):
        admin_auth = self.load_admin_auth()

        cookie = admin_auth.build_session_cookie("token-value", 3600)

        self.assertIn("blt_admin_session=token-value", cookie)
        self.assertIn("Max-Age=3600", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        self.assertIn("Path=/", cookie)

    def test_clear_session_cookie_expires_cookie(self):
        admin_auth = self.load_admin_auth()

        cookie = admin_auth.build_clear_session_cookie()

        self.assertIn("blt_admin_session=", cookie)
        self.assertIn("Max-Age=0", cookie)
        self.assertIn("Expires=Thu, 01 Jan 1970 00:00:00 GMT", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        self.assertIn("Path=/", cookie)

    def test_parse_cookie_returns_cookie_values(self):
        admin_auth = self.load_admin_auth()

        parsed = admin_auth.parse_cookie("theme=dark; blt_admin_session=abc123; other=value")

        self.assertEqual(parsed["theme"], "dark")
        self.assertEqual(parsed["blt_admin_session"], "abc123")


class AdminWorkerRouteTests(unittest.TestCase):
    def load_entry_with_worker_fakes(self):
        class FakeHeaders(dict):
            @classmethod
            def new(cls, pairs):
                return cls(pairs)

        class FakeResponse:
            @classmethod
            def new(cls, body, status=200, headers=None):
                return types.SimpleNamespace(body=body, status=status, headers=headers)

        fake_js = types.ModuleType("js")
        fake_js.Headers = FakeHeaders
        fake_js.Request = type("Request", (), {})
        fake_js.Response = FakeResponse
        fake_js.URL = type("URL", (), {})

        fake_workers = types.ModuleType("workers")
        fake_workers.WorkerEntrypoint = type("WorkerEntrypoint", (), {})

        original_entry = sys.modules.pop("src.entry", None)
        try:
            with mock.patch.dict(
                sys.modules,
                {
                    "js": fake_js,
                    "workers": fake_workers,
                },
            ):
                return importlib.import_module("src.entry")
        finally:
            sys.modules.pop("src.entry", None)
            if original_entry is not None:
                sys.modules["src.entry"] = original_entry

    def test_worker_declares_admin_and_campaign_api_routes(self):
        entrypoint = (ROOT / "src" / "entry.py").read_text()

        for route in [
            '"/api/admin/login"',
            '"/api/admin/logout"',
            '"/api/admin/me"',
            '"/api/admin/stats"',
            '"/api/admin/subscribers"',
            '"/api/admin/campaigns"',
            '"/api/campaigns"',
        ]:
            self.assertIn(route, entrypoint)

        self.assertIn("handle_admin_login", entrypoint)
        self.assertIn("handle_admin_logout", entrypoint)
        self.assertIn("handle_admin_me", entrypoint)
        self.assertIn("handle_admin_stats", entrypoint)
        self.assertIn("handle_admin_subscribers", entrypoint)
        self.assertIn("handle_admin_campaigns", entrypoint)
        self.assertIn("handle_public_campaigns", entrypoint)
        self.assertIn("handle_public_campaign_detail", entrypoint)

    def test_worker_declares_sendgrid_campaign_and_job_routes(self):
        entrypoint = (ROOT / "src" / "entry.py").read_text()

        for route_or_handler in [
            "send-test",
            '"/publish"',
            '"/api/admin/jobs"',
            "handle_admin_send_test",
            "handle_admin_publish_campaign",
            "handle_admin_jobs",
            "handle_admin_job_detail",
            "handle_admin_cancel_job",
            "handle_admin_retry_failed_job",
            '"/retry-failed"',
            "async def queue(self, batch, env=None, ctx=None)",
        ]:
            self.assertIn(route_or_handler, entrypoint)

        for store_method in [
            "list_active_subscribers",
            "find_subscriber_by_id",
            "insert_send_job",
            "list_send_jobs",
            "find_send_job_by_id",
            "insert_delivery_event",
            "list_delivery_events_for_job",
            "list_failed_delivery_events_for_job",
            "list_retryable_failed_delivery_events_for_job",
            "increment_send_job_counts",
            "mark_failed_deliveries_requeued",
        ]:
            self.assertIn(f"async def {store_method}", entrypoint)

        self.assertIn("def d1_rows_changed", entrypoint)

        self.assertIn("NEWSLETTER_QUEUE", entrypoint)
        self.assertIn("SENDGRID_API_KEY", entrypoint)

    def test_worker_declares_admin_settings_routes_and_store_methods(self):
        entrypoint = (ROOT / "src" / "entry.py").read_text()
        migration = (ROOT / "migrations" / "0001_newsletter_schema.sql").read_text()

        for expected in [
            '"/api/admin/settings"',
            "handle_admin_settings",
            "handle_admin_update_settings",
            "build_admin_settings_updates",
            "list_settings",
            "upsert_settings",
        ]:
            self.assertIn(expected, entrypoint)

        self.assertIn("CREATE TABLE IF NOT EXISTS newsletter_settings", migration)
        self.assertIn("setting_key TEXT PRIMARY KEY", migration)
        self.assertIn("setting_value TEXT NOT NULL", migration)

    def test_admin_update_settings_persists_sender_identity(self):
        entry = self.load_entry_with_worker_fakes()

        class FakeRequest:
            async def json(self):
                return {
                    "from_name": "BLT Dispatch",
                    "from_email": "newsletter@example.com",
                    "reply_to_email": "support@example.com",
                }

        class FakeStore:
            def __init__(self):
                self.saved = None

            async def upsert_settings(self, settings, admin_id, updated_at):
                self.saved = (dict(settings), admin_id, updated_at)

            async def list_settings(self, keys=None):
                return self.saved[0] if self.saved else {}

        store = FakeStore()
        worker = entry.Default()
        worker.env = {}

        async def fake_require_admin(_request):
            return {
                "store": store,
                "session": {"id": "session_1"},
                "admin": {"id": "admin_1"},
            }, None

        worker.require_admin = fake_require_admin

        response = asyncio.run(worker.handle_admin_update_settings(FakeRequest()))
        payload = json.loads(response.body)

        self.assertEqual(response.status, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["settings"]["from_name"], "BLT Dispatch")
        self.assertEqual(payload["settings"]["from_email"], "newsletter@example.com")
        self.assertEqual(payload["settings"]["reply_to_email"], "support@example.com")
        self.assertEqual(store.saved[0]["from_name"], "BLT Dispatch")
        self.assertEqual(store.saved[1], "admin_1")

    def test_worker_queue_handler_accepts_runtime_env_and_context_arguments(self):
        entry = self.load_entry_with_worker_fakes()
        signature = inspect.signature(entry.Default.queue)
        parameters = list(signature.parameters.values())

        self.assertEqual(
            [parameter.name for parameter in parameters],
            ["self", "batch", "env", "ctx"],
        )
        self.assertEqual(parameters[2].default, None)
        self.assertEqual(parameters[3].default, None)

        worker = entry.Default()
        worker.env = {}

        asyncio.run(worker.queue({"messages": []}, object(), object()))

    def test_retry_failed_job_requeues_latest_failed_deliveries(self):
        entry = self.load_entry_with_worker_fakes()

        actions = []

        class FakeQueue:
            def __init__(self):
                self.messages = []

            async def send(self, payload):
                actions.append("send")
                self.messages.append(payload)

        class FakeStore:
            def __init__(self):
                self.inserted_events = []
                self.requeued = None

            async def find_send_job_by_id(self, job_id):
                failed_count = 2
                if self.requeued:
                    failed_count -= self.requeued[1]
                return {
                    "id": job_id,
                    "campaign_id": "campaign_1",
                    "status": "completed",
                    "total_recipients": 4,
                    "sent_count": 1,
                    "failed_count": max(failed_count, 0),
                    "skipped_count": 1,
                }

            async def list_retryable_failed_delivery_events_for_job(self, job_id):
                return [
                    {"id": "event_failed_1", "subscriber_id": "subscriber_1"},
                    {"id": "event_failed_2", "subscriber_id": "subscriber_2"},
                ]

            async def insert_delivery_event(self, record):
                actions.append("insert")
                self.inserted_events.append(record)

            async def mark_failed_deliveries_requeued(self, job_id, retry_count):
                actions.append("mark")
                self.requeued = (job_id, retry_count)
                return True

        queue = FakeQueue()
        store = FakeStore()
        worker = entry.Default()
        worker.env = {
            "SENDGRID_API_KEY": "test-key",
            "SENDGRID_FROM_EMAIL": "sender@example.com",
            "NEWSLETTER_QUEUE": queue,
        }

        async def fake_require_admin(_request):
            return {"store": store, "session": {"id": "session_1"}, "admin": {}}, None

        worker.require_admin = fake_require_admin

        response = asyncio.run(
            worker.handle_admin_retry_failed_job(types.SimpleNamespace(headers={}), "job_1")
        )
        payload = json.loads(response.body)

        self.assertEqual(response.status, 202)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["retried_count"], 2)
        self.assertEqual(payload["job"]["failed_count"], 0)
        self.assertEqual(store.requeued, ("job_1", 2))
        self.assertEqual(actions[0], "mark")
        self.assertEqual(actions.count("send"), 2)
        self.assertEqual(len(store.inserted_events), 2)
        self.assertEqual(len(queue.messages), 2)
        self.assertEqual(queue.messages[0]["job_id"], "job_1")
        self.assertEqual(queue.messages[0]["campaign_id"], "campaign_1")
        self.assertEqual(queue.messages[0]["subscriber_id"], "subscriber_1")

        first_event = store.inserted_events[0]
        self.assertEqual(first_event["event_type"], "queued")
        self.assertEqual(first_event["subscriber_id"], "subscriber_1")
        self.assertEqual(
            json.loads(first_event["metadata_json"])["retry_of_event_id"],
            "event_failed_1",
        )

    def test_unsubscribe_links_campaign_publish_and_duplicate_send_guards_are_present(self):
        entrypoint = (ROOT / "src" / "entry.py").read_text()

        for expected in [
            '"/unsubscribe"',
            "handle_public_unsubscribe_page",
            "build_unsubscribe_token",
            "verify_unsubscribe_token",
            "mark_subscriber_unsubscribed_by_id",
            "find_open_send_job_by_campaign",
        ]:
            self.assertIn(expected, entrypoint)

        self.assertIn("Email sending is not configured", entrypoint)
        self.assertIn("Campaign already queued.", entrypoint)
        self.assertIn('"status": "published"', entrypoint)
        self.assertIn("published_at", entrypoint)

    def test_d1_admin_store_declares_required_session_methods(self):
        entrypoint = (ROOT / "src" / "entry.py").read_text()

        for method_name in [
            "find_admin_by_email_hash",
            "update_admin_last_login",
            "insert_admin_session",
            "find_active_session",
            "revoke_session",
        ]:
            self.assertIn(f"async def {method_name}", entrypoint)

        self.assertIn("newsletter_admins", entrypoint)
        self.assertIn("newsletter_admin_sessions", entrypoint)
        self.assertIn("revoked_at IS NULL", entrypoint)
        self.assertRegex(entrypoint, r"expires_at\s*>\s*\?")

    def test_first_admin_setup_routes_and_store_are_one_time_only(self):
        entrypoint = (ROOT / "src" / "entry.py").read_text()

        for route in [
            '"/signup"',
            '"/api/admin/setup/status"',
            '"/api/admin/setup"',
        ]:
            self.assertIn(route, entrypoint)

        for method_name in [
            "handle_signup_page",
            "handle_admin_setup_status",
            "handle_admin_setup",
            "admin_count",
            "insert_admin",
        ]:
            self.assertIn(method_name, entrypoint)

        self.assertIn("SELECT COUNT(*) AS total_admins", entrypoint)
        self.assertIn("if admin_count > 0", entrypoint)
        self.assertIn("First admin is already configured.", entrypoint)
        self.assertIn('redirect_to(request, "/login", 302)', entrypoint)
        self.assertIn('redirect_to(request, "/signup", 302)', entrypoint)
        self.assertIn("def redirect_to(request, pathname, status=302):", entrypoint)

    def test_first_admin_setup_record_hashes_password_and_sets_safe_defaults(self):
        entrypoint = (ROOT / "src" / "entry.py").read_text()

        self.assertIn("hash_password(password)", entrypoint)
        self.assertIn('"role": "admin"', entrypoint)
        self.assertIn('"status": "active"', entrypoint)
        self.assertIn('"metadata_json": "{}"', entrypoint)
        self.assertIn('"last_login_at": now', entrypoint)
        self.assertNotIn('"password_hash": password', entrypoint)

    def test_public_campaigns_route_source_only_returns_published_campaigns(self):
        entrypoint = (ROOT / "src" / "entry.py").read_text()

        self.assertIn('"/api/campaigns"', entrypoint)
        self.assertIn("WHERE status = 'published'", entrypoint)
        self.assertNotRegex(
            entrypoint,
            r"handle_public_campaigns[\s\S]+WHERE status != 'deleted'",
        )

    def test_migration_uses_slug_summary_and_published_at_for_campaigns(self):
        migration = (ROOT / "migrations" / "0001_newsletter_schema.sql").read_text()

        self.assertIn("slug TEXT NOT NULL UNIQUE", migration)
        self.assertIn("summary TEXT", migration)
        self.assertIn("published_at TEXT", migration)
        self.assertNotIn("campaign_slug", migration)

    def test_send_jobs_track_skipped_deliveries_for_delivery_panel(self):
        initial_migration = (ROOT / "migrations" / "0001_newsletter_schema.sql").read_text()
        skipped_migration = (ROOT / "migrations" / "0002_send_job_skipped_count.sql").read_text()
        entrypoint = (ROOT / "src" / "entry.py").read_text()

        self.assertNotIn("skipped_count INTEGER NOT NULL DEFAULT 0", initial_migration)
        self.assertIn("ADD COLUMN skipped_count INTEGER NOT NULL DEFAULT 0", skipped_migration)
        self.assertIn("skipped_count", entrypoint)
        self.assertIn("skipped_delta", entrypoint)

    def test_all_d1_migrations_apply_to_empty_database(self):
        connection = sqlite3.connect(":memory:")
        try:
            for migration in sorted((ROOT / "migrations").glob("*.sql")):
                connection.executescript(migration.read_text())
        finally:
            connection.close()

    def test_campaign_create_record_is_d1_safe_without_none_values(self):
        entrypoint = (ROOT / "src" / "entry.py").read_text()

        self.assertIn('"summary": clean_optional_text(payload.get("summary")) or ""', entrypoint)
        self.assertIn('"html_body": ""', entrypoint)
        self.assertIn('"scheduled_for": ""', entrypoint)
        self.assertIn('"published_at": ""', entrypoint)
        self.assertIn('"sent_at": ""', entrypoint)
        self.assertIn("return cleaned or \"\"", entrypoint)

    def test_d1_campaign_store_uses_schema_compatibility_helpers(self):
        entrypoint = (ROOT / "src" / "entry.py").read_text()

        for expected in [
            "campaign_table_columns",
            "campaign_table_name",
            "campaign_select_columns",
            "campaign_slug_column",
            "campaign_order_expression",
            "campaign_insert_columns_and_params",
            "map_campaign_update_fields",
            "send_job_campaign_column",
            "sqlite_master",
            "pragma_table_info",
        ]:
            self.assertIn(expected, entrypoint)


class AdminSeedScriptTests(unittest.TestCase):
    def test_seed_script_imports_helpers_and_prints_insert_sql(self):
        script = ROOT / "scripts" / "seed_admin.py"
        if not script.exists():
            self.fail("scripts/seed_admin.py must print local admin seed SQL")

        source = script.read_text()
        self.assertIn("from src.admin_auth import hash_password", source)
        self.assertIn("from src.newsletter_validation import email_hash", source)
        self.assertIn("from src.newsletter_validation import normalize_email", source)

        env = dict(os.environ)
        env["EMAIL_HASH_SECRET"] = "seed-test-secret"
        short_password = subprocess.run(
            [
                sys.executable,
                str(script),
                "--email",
                "Admin@Example.COM",
                "--password",
                "short",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertNotEqual(short_password.returncode, 0)
        self.assertIn("at least 8 characters", short_password.stderr)

        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--email",
                "Admin@Example.COM",
                "--password",
                "CorrectHorse123!",
                "--name",
                "Site Admin",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("INSERT INTO newsletter_admins", result.stdout)
        self.assertIn("admin@example.com", result.stdout)
        self.assertIn(email_hash("admin@example.com", "seed-test-secret"), result.stdout)
        self.assertIn("pbkdf2_sha256$", result.stdout)
        self.assertNotIn("CorrectHorse123!", result.stdout)


class AdminFrontendWiringTests(unittest.TestCase):
    def test_login_page_posts_to_admin_login_and_does_not_redirect_unconditionally(self):
        page = (ROOT / "public" / "login.html").read_text()

        self.assertIn('fetch("/api/admin/login"', page)
        self.assertIn('method: "POST"', page)
        self.assertIn("login-error", page)
        self.assertNotRegex(
            page,
            re.compile(
                r"function\s+login\s*\(\)\s*\{\s*window\.location\.href\s*=\s*['\"]/dashboard['\"]\s*;",
                re.MULTILINE,
            ),
        )

    def test_login_page_redirects_to_first_admin_signup_when_no_admin_exists(self):
        page = (ROOT / "public" / "login.html").read_text()

        self.assertIn("checkFirstAdminSetup", page)
        self.assertIn('fetch("/api/admin/setup/status"', page)
        self.assertIn("payload.setup_required", page)
        self.assertIn("window.location.href = '/signup'", page)

    def test_first_admin_signup_page_posts_to_setup_api_and_redirects_after_success(self):
        page_path = ROOT / "public" / "signup.html"
        self.assertTrue(page_path.exists())
        page = page_path.read_text()

        self.assertIn('id="signup-page"', page)
        self.assertIn('fetch("/api/admin/setup/status"', page)
        self.assertIn('fetch("/api/admin/setup"', page)
        self.assertIn('method: "POST"', page)
        self.assertIn('credentials: "same-origin"', page)
        self.assertIn("payload.setup_required === false", page)
        self.assertIn("window.location.href = '/login'", page)
        self.assertIn("window.location.href = '/dashboard'", page)
        self.assertIn("First admin", page)

    def test_dashboard_logout_posts_to_admin_logout(self):
        page = (ROOT / "public" / "dashboard.html").read_text()

        self.assertIn('fetch("/api/admin/logout"', page)
        self.assertIn('method: "POST"', page)
        self.assertIn("window.location.href = '/login'", page)

    def test_dashboard_bootstrap_fetches_real_admin_apis_with_auth_redirect(self):
        page = (ROOT / "public" / "dashboard.html").read_text()

        self.assertIn("document.addEventListener('DOMContentLoaded', initializeDashboard)", page)
        for endpoint in [
            "/api/admin/me",
            "/api/admin/stats",
            "/api/admin/subscribers",
            "/api/admin/campaigns",
        ]:
            self.assertIn(f'adminFetch("{endpoint}"', page)
        self.assertIn('credentials: "same-origin"', page)
        self.assertIn("if (response.status === 401)", page)
        self.assertIn("window.location.href = '/login'", page)

    def test_dashboard_renders_subscribers_and_campaigns_from_api_not_static_mock_rows(self):
        page = (ROOT / "public" / "dashboard.html").read_text()

        for element_id in [
            "admin-avatar-initials",
            "stat-active-subscribers",
            "stat-new-subscribers",
            "stat-published-campaigns",
            "stat-draft-campaigns",
            "campaign-recipient-count",
            "users-table-body",
            "campaigns-table-body",
        ]:
            self.assertIn(f'id="{element_id}"', page)

        self.assertIn("function renderSubscribers(subscribers)", page)
        self.assertIn("function renderCampaigns(campaigns)", page)
        self.assertIn("function renderEmptyRow", page)
        self.assertNotIn("Aisha Khan", page)
        self.assertNotIn("BLT Monthly Digest — June 2026", page)

    def test_dashboard_campaign_editor_saves_drafts_to_campaign_api(self):
        page = (ROOT / "public" / "dashboard.html").read_text()

        for element_id in [
            "campaign-title",
            "campaign-slug",
            "campaign-subject",
            "campaign-summary",
            "campaign-markdown-body",
        ]:
            self.assertIn(f'id="{element_id}"', page)
        self.assertIn("async function saveCampaignDraft()", page)
        self.assertIn('adminFetch("/api/admin/campaigns", {', page)
        self.assertIn('method: "POST"', page)
        self.assertIn('method: "PATCH"', page)
        self.assertIn("renderCampaigns(dashboardState.campaigns)", page)

    def test_dashboard_send_test_and_campaign_controls_call_backend_apis(self):
        page = (ROOT / "public" / "dashboard.html").read_text()

        self.assertIn("async function sendTestEmail()", page)
        self.assertIn("async function publishCampaign()", page)
        self.assertIn("function renderDeliveryJobs(jobs)", page)
        self.assertIn("adminFetch(`/api/admin/campaigns/${", page)
        self.assertIn("/send-test`, {", page)
        self.assertIn("/publish`, {", page)
        self.assertIn('adminFetch("/api/admin/jobs"', page)
        self.assertIn('id="test-email-recipient"', page)
        self.assertIn("campaign-recipient-count", page)

    def test_dashboard_delivery_details_uses_real_job_detail_data(self):
        page = (ROOT / "public" / "dashboard.html").read_text()

        for element_id in [
            "delivery-details-sent",
            "delivery-details-failed",
            "delivery-details-skipped",
            "delivery-details-progress-fill",
            "delivery-details-progress-text",
            "delivery-details-failed-list",
            "retry-failed-deliveries-btn",
        ]:
            self.assertIn(f'id="{element_id}"', page)

        self.assertIn("async function openDeliveryDetails(jobId)", page)
        self.assertIn("function renderDeliveryDetails(job, failedEvents", page)
        self.assertIn("async function retryFailedDeliveries()", page)
        self.assertIn("adminFetch(`/api/admin/jobs/${encodeURIComponent(jobId)}`", page)
        self.assertIn("/retry-failed`, {", page)
        self.assertNotIn("marcus.johnson@example.com", page)
        self.assertNotIn("sofia.garcia@example.com", page)
        self.assertNotIn(">1,248<", page)

    def test_dashboard_settings_save_calls_admin_settings_api(self):
        page = (ROOT / "public" / "dashboard.html").read_text()

        for element_id in [
            "settings-from-name",
            "settings-from-email",
            "settings-reply-to-email",
            "settings-save-button",
        ]:
            self.assertIn(f'id="{element_id}"', page)

        self.assertIn("async function loadSettings()", page)
        self.assertIn("async function saveSettings()", page)
        self.assertIn('adminFetch("/api/admin/settings"', page)
        self.assertIn('method: "PATCH"', page)
        self.assertIn("renderSettings(payload.settings", page)
        self.assertNotIn("onclick=\"showToast('Settings saved')\"", page)

    def test_dashboard_uses_data_attributes_for_api_ids_instead_of_inline_js_strings(self):
        page = (ROOT / "public" / "dashboard.html").read_text()

        self.assertIn("data-subscriber-id", page)
        self.assertIn("data-campaign-id", page)
        self.assertIn("data-job-id", page)
        self.assertIn("addEventListener('click', handleDashboardTableActions)", page)
        self.assertNotIn("onclick=\"openUserDetails('${id}')", page)
        self.assertNotIn("onclick=\"openCampaignEditor('${id}')", page)
        self.assertNotIn("onclick=\"openCampaignDetails('${id}')", page)


if __name__ == "__main__":
    unittest.main()
