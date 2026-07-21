from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migrations" / "0001_initial.sql"


class SchemaContractTests(unittest.TestCase):
    def read_migration(self):
        if not MIGRATION.exists():
            self.fail("migrations/0001_initial.sql must exist")
        return MIGRATION.read_text()

    def test_baseline_contains_only_blt_timer_tables(self):
        sql = self.read_migration()

        for table in ["users", "auth_sessions", "work_logs"]:
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {table}", sql)

        for retired_table in ["sessions", "activities"]:
            self.assertNotRegex(
                sql,
                rf"CREATE TABLE IF NOT EXISTS {retired_table}\s*\(",
            )

    def test_users_schema_has_local_auth_identity_fields(self):
        sql = self.read_migration()

        for expected in [
            "id TEXT PRIMARY KEY",
            "username TEXT NOT NULL UNIQUE",
            "email TEXT NOT NULL UNIQUE",
            "password_hash TEXT NOT NULL",
            "display_name TEXT",
            "timezone TEXT NOT NULL DEFAULT 'UTC'",
            "created_at INTEGER NOT NULL",
            "updated_at INTEGER NOT NULL",
        ]:
            self.assertIn(expected, sql)

    def test_auth_sessions_schema_stores_only_hashed_session_tokens(self):
        sql = self.read_migration()

        for expected in [
            "user_id TEXT NOT NULL",
            "session_token_hash TEXT NOT NULL UNIQUE",
            "expires_at INTEGER NOT NULL",
            "last_seen_at INTEGER",
            "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE",
        ]:
            self.assertIn(expected, sql)

        self.assertNotIn("session_token TEXT", sql)

    def test_work_logs_schema_has_minimal_time_log_fields(self):
        sql = self.read_migration()

        for expected in [
            "title TEXT NOT NULL",
            "notes TEXT",
            "project TEXT",
            "reference_url TEXT",
            "source TEXT NOT NULL DEFAULT 'web'",
            "start_time INTEGER NOT NULL",
            "end_time INTEGER NOT NULL",
            "duration_seconds INTEGER NOT NULL",
        ]:
            self.assertIn(expected, sql)

    def test_indexes_support_user_scoped_history_and_sessions(self):
        sql = self.read_migration()

        for expected in [
            "idx_auth_sessions_user_id",
            "idx_auth_sessions_token_hash",
            "idx_work_logs_user_start_time",
            "idx_work_logs_user_project",
            "idx_work_logs_user_created_at",
        ]:
            self.assertIn(expected, sql)


if __name__ == "__main__":
    unittest.main()
