"""Apply NetGuardian D1 migration against SQLite (CI-friendly)."""

import sqlite3
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
INGEST_MIGRATION = REPO_ROOT / "migrations" / "0002_ingest_core.sql"


def _apply_sql(conn: sqlite3.Connection, path: Path) -> None:
    conn.executescript(path.read_text())
    conn.commit()


def test_ng_migration_applies_on_fresh_sqlite():
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        _apply_sql(conn, INGEST_MIGRATION)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for name in (
            "sender_keys",
            "envelopes",
            "findings",
            "evidence_meta",
            "access_logs",
            "events_outbox",
            "ng_metrics",
        ):
            assert name in tables

        conn.execute(
            """
            INSERT INTO envelopes (
              id, org_id, sender_id, kid, nonce, digest, payload_digest,
              issued_at, received_at, payload_json
            ) VALUES (
              'env1', 'org1', 'sender1', 'k1', 'n1', 'd1', 'pd1',
              1, 1, '{}'
            )
            """
        )
        conn.execute(
            """
            INSERT INTO findings (
              id, org_id, envelope_id, rule_id, severity, title,
              created_at, updated_at
            ) VALUES (
              'fnd1', 'org1', 'env1', 'rule', 'high', 't', 1, 1
            )
            """
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO envelopes (
                  id, org_id, sender_id, kid, nonce, digest, payload_digest,
                  issued_at, received_at, payload_json
                ) VALUES (
                  'env2', 'org1', 'sender1', 'k1', 'n1', 'd2', 'pd2',
                  2, 2, '{}'
                )
                """
            )
    finally:
        conn.close()
