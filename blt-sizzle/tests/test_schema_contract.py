import re
import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migrations" / "0004_app_refactor_auth_orgs.sql"


class TestAppRefactorSchemaContract(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MIGRATION.exists(), "0004 app refactor migration must exist")
        self.sql = MIGRATION.read_text()
        self.normalized = re.sub(r"\s+", " ", self.sql.lower())

    def assertContainsSql(self, fragment):
        self.assertIn(fragment.lower(), self.normalized)

    def test_auth_sessions_table_exists(self):
        self.assertContainsSql("create table if not exists auth_sessions")
        for column in ["session_hash", "user_id", "expires_at", "last_seen_at"]:
            self.assertIn(column, self.normalized)

    def test_email_otps_table_exists(self):
        self.assertContainsSql("create table if not exists email_otps")
        for column in ["email", "otp_hash", "purpose", "attempts", "expires_at", "consumed_at"]:
            self.assertIn(column, self.normalized)

    def test_generic_org_columns_are_added(self):
        for fragment in [
            "alter table organizations add column name",
            "alter table organizations add column slug",
            "alter table organizations add column description",
            "alter table organizations add column created_by_user_id",
            "alter table organizations add column default_timezone",
            "alter table organizations add column checkin_enabled",
        ]:
            self.assertContainsSql(fragment)

    def test_membership_role_and_approval_columns_are_added(self):
        for fragment in [
            "alter table user_organizations add column role",
            "alter table user_organizations add column requested_at",
            "alter table user_organizations add column approved_by_user_id",
            "alter table user_organizations add column approved_at",
        ]:
            self.assertContainsSql(fragment)

    def test_checkin_index_and_updated_at_are_added(self):
        self.assertContainsSql("alter table checkins add column updated_at")
        self.assertContainsSql("create index if not exists idx_checkins_org_user_date")
        self.assertNotIn("create unique index if not exists idx_checkins_org_user_date", self.normalized)
        self.assertContainsSql("org_id, user_id, checkin_date")

    def test_migration_executes_on_non_empty_legacy_schema_with_duplicates(self):
        connection = sqlite3.connect(":memory:")
        connection.executescript(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                encrypted_email TEXT,
                encrypted_display_name TEXT,
                slack_user_id TEXT,
                encrypted_slack_webhook_url TEXT,
                notification_time TEXT DEFAULT '09:00',
                notification_enabled INTEGER DEFAULT 1,
                email_notifications INTEGER DEFAULT 0,
                timezone TEXT DEFAULT 'UTC',
                current_streak INTEGER DEFAULT 0,
                longest_streak INTEGER DEFAULT 0,
                last_check_in DATE,
                github_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                github_org_name TEXT UNIQUE NOT NULL,
                encrypted_slack_webhook_url TEXT,
                encrypted_org_key TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE user_organizations (
                user_id TEXT NOT NULL,
                org_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'approved',
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, org_id)
            );
            CREATE TABLE checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                encrypted_previous_work TEXT,
                encrypted_today_plan TEXT,
                encrypted_blockers TEXT,
                mood TEXT,
                goal_accomplished INTEGER DEFAULT 0,
                checkin_date DATE NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                org_id INTEGER
            );
            INSERT INTO users (user_id) VALUES ('alice');
            INSERT INTO organizations (github_org_name) VALUES ('owasp-blt');
            INSERT INTO user_organizations (user_id, org_id, status) VALUES ('alice', 1, 'approved');
            INSERT INTO checkins (user_id, checkin_date, org_id) VALUES ('alice', '2026-06-28', 1);
            INSERT INTO checkins (user_id, checkin_date, org_id) VALUES ('alice', '2026-06-28', 1);
            """
        )

        connection.executescript(self.sql)

        org_columns = {row[1] for row in connection.execute("PRAGMA table_info(organizations)")}
        membership_columns = {row[1] for row in connection.execute("PRAGMA table_info(user_organizations)")}
        checkin_columns = {row[1] for row in connection.execute("PRAGMA table_info(checkins)")}
        self.assertIn("slug", org_columns)
        self.assertIn("role", membership_columns)
        self.assertIn("requested_at", membership_columns)
        self.assertIn("updated_at", checkin_columns)
        self.assertEqual(
            connection.execute("SELECT slug FROM organizations WHERE id = 1").fetchone()[0],
            "owasp-blt",
        )

    def test_legacy_github_columns_are_not_dropped_in_transition_migration(self):
        self.assertNotIn("drop column github", self.normalized)
        self.assertNotIn("drop table organizations", self.normalized)


if __name__ == "__main__":
    unittest.main(verbosity=2)
