import asyncio
import unittest
from pathlib import Path

from src.newsletter_service import subscribe, unsubscribe
from src.newsletter_validation import email_hash, is_valid_email, normalize_email


ROOT = Path(__file__).resolve().parents[1]
SECRET = "test-email-hash-secret"


class FakeSubscriberStore:
    def __init__(self):
        self.records = {}

    async def find_by_hash(self, subscriber_hash):
        return self.records.get(subscriber_hash)

    async def insert_subscriber(self, record):
        self.records[record["email_hash"]] = dict(record)

    async def reactivate_subscriber(self, subscriber_hash, updates):
        record = self.records[subscriber_hash]
        record.update(updates)

    async def mark_unsubscribed(self, subscriber_hash, unsubscribed_at):
        record = self.records.get(subscriber_hash)
        if record is not None:
            record["status"] = "unsubscribed"
            record["unsubscribed_at"] = unsubscribed_at


class NewsletterBackendTests(unittest.TestCase):
    def test_email_validation_normalizes_and_validates(self):
        self.assertEqual(
            normalize_email("  Security.Editor+BLT@Example.COM  "),
            "security.editor+blt@example.com",
        )
        self.assertTrue(is_valid_email("security.editor+blt@example.com"))
        self.assertFalse(is_valid_email("not-an-email"))
        self.assertFalse(is_valid_email("person@localhost"))
        self.assertFalse(is_valid_email(""))

    def test_email_hash_is_deterministic_and_not_plain_email(self):
        normalized = normalize_email("User@Example.com")

        first_hash = email_hash(normalized, SECRET)
        second_hash = email_hash(normalized, SECRET)

        self.assertEqual(first_hash, second_hash)
        self.assertNotEqual(first_hash, normalized)
        self.assertNotIn("user", first_hash)
        self.assertEqual(len(first_hash), 64)

    def test_migration_declares_required_tables(self):
        migration = (ROOT / "migrations" / "0001_newsletter_schema.sql").read_text()

        for table_name in [
            "newsletter_subscribers",
            "newsletter_admins",
            "newsletter_admin_sessions",
            "newsletter_campaigns",
            "newsletter_send_jobs",
            "newsletter_delivery_events",
            "newsletter_rate_limits",
        ]:
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {table_name}", migration)

        self.assertIn("email_hash TEXT NOT NULL UNIQUE", migration)
        self.assertIn("status TEXT NOT NULL DEFAULT 'active'", migration)
        self.assertIn("consent_version TEXT NOT NULL DEFAULT '2026-06-14'", migration)

    def test_worker_declares_subscribe_unsubscribe_routes(self):
        entrypoint = (ROOT / "src" / "entry.py").read_text()

        self.assertIn('"/api/subscribe"', entrypoint)
        self.assertIn('"/api/unsubscribe"', entrypoint)
        self.assertIn('"OPTIONS"', entrypoint)
        self.assertIn("EMAIL_HASH_SECRET", entrypoint)
        self.assertIn("safe_json", entrypoint)

    def test_d1_store_converts_python_none_to_js_null_before_binding(self):
        entrypoint = (ROOT / "src" / "entry.py").read_text()

        self.assertIn("from pyodide.ffi import to_js", entrypoint)
        self.assertIn("def bind_statement", entrypoint)
        self.assertIn("to_js(list(params))", entrypoint)

    def test_json_responses_use_workers_headers_object(self):
        entrypoint = (ROOT / "src" / "entry.py").read_text()

        self.assertIn("from js import Headers", entrypoint)
        self.assertIn("Headers.new(list(headers.items()))", entrypoint)
        self.assertIn("Headers.new(list(CORS_HEADERS.items()))", entrypoint)

    def test_landing_page_posts_to_api_subscribe_not_gitlab_issues(self):
        page = (ROOT / "public" / "index.html").read_text()

        self.assertIn('fetch("/api/subscribe"', page)
        self.assertNotIn("GITLAB_API", page)
        self.assertNotIn("GITLAB_PROJECT", page)
        self.assertNotIn("gitlab.com/api/v4", page)
        self.assertNotIn("newsletter-subscription", page)
        self.assertNotIn("GitHub Issues", page)
        self.assertNotIn("Drop an issue", page)
        self.assertNotIn("GitHub-first delivery", page)
        self.assertNotIn("GitHub-native subscriptions", page)

    def test_unsubscribe_privacy_safe_logic(self):
        async def run_case():
            store = FakeSubscriberStore()
            existing_hash = email_hash("known@example.com", SECRET)
            store.records[existing_hash] = {
                "id": "sub_known",
                "email": "known@example.com",
                "email_hash": existing_hash,
                "status": "active",
                "unsubscribed_at": None,
            }

            known = await unsubscribe(
                store,
                {"email": "known@example.com"},
                SECRET,
                now_func=lambda: "2026-06-17T00:00:00Z",
            )
            unknown = await unsubscribe(
                store,
                {"email": "unknown@example.com"},
                SECRET,
                now_func=lambda: "2026-06-17T00:00:00Z",
            )

            self.assertTrue(known["success"])
            self.assertTrue(unknown["success"])
            self.assertEqual(known["message"], unknown["message"])
            self.assertEqual(store.records[existing_hash]["status"], "unsubscribed")
            self.assertEqual(
                store.records[existing_hash]["unsubscribed_at"],
                "2026-06-17T00:00:00Z",
            )

        asyncio.run(run_case())

    def test_subscribe_is_idempotent_and_reactivates_unsubscribed_users(self):
        async def run_case():
            store = FakeSubscriberStore()

            first = await subscribe(
                store,
                {"email": "User@Example.com", "name": "  User  Name  ", "consent": True},
                SECRET,
                now_func=lambda: "2026-06-17T00:00:00Z",
                id_factory=lambda: "sub_first",
            )
            second = await subscribe(
                store,
                {"email": "user@example.com", "consent": True},
                SECRET,
                now_func=lambda: "2026-06-17T00:01:00Z",
                id_factory=lambda: "sub_second",
            )

            subscriber_hash = email_hash("user@example.com", SECRET)
            store.records[subscriber_hash]["status"] = "unsubscribed"
            store.records[subscriber_hash]["unsubscribed_at"] = "2026-06-17T00:02:00Z"

            reactivated = await subscribe(
                store,
                {"email": "user@example.com", "consent": True},
                SECRET,
                now_func=lambda: "2026-06-17T00:03:00Z",
                id_factory=lambda: "sub_reactivated",
            )

            self.assertTrue(first["success"])
            self.assertEqual(first["status"], "active")
            self.assertTrue(second["success"])
            self.assertEqual(second["message"], "You are already subscribed.")
            self.assertTrue(reactivated["success"])
            self.assertEqual(store.records[subscriber_hash]["id"], "sub_first")
            self.assertEqual(store.records[subscriber_hash]["status"], "active")
            self.assertIsNone(store.records[subscriber_hash]["unsubscribed_at"])
            self.assertEqual(
                store.records[subscriber_hash]["subscribed_at"],
                "2026-06-17T00:03:00Z",
            )

        asyncio.run(run_case())
    def test_subscribe_builds_d1_safe_record_without_none_values(self):
        async def run_case():
            store = FakeSubscriberStore()

            await subscribe(
                store,
                {"email": "none-safe@example.com", "consent": True},
                SECRET,
                now_func=lambda: "2026-06-17T00:00:00Z",
                id_factory=lambda: "sub_none_safe",
            )

            subscriber_hash = email_hash("none-safe@example.com", SECRET)
            record = store.records[subscriber_hash]
            self.assertNotIn(None, record.values())
            self.assertEqual(record["name"], "")
            self.assertEqual(record["unsubscribed_at"], "")
            self.assertEqual(record["last_sent_at"], "")

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
