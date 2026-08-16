"""Apply NetGuardian D1 migrations against SQLite (CI-friendly)."""

import sqlite3
from pathlib import Path

import pytest

from netguardian_db import open_netguardian_db

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_ng_migration_applies_on_fresh_sqlite():
    db = open_netguardian_db(REPO_ROOT)
    conn = db.conn
    try:
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
            "oauth_states",
            "auth_sessions",
        ):
            assert name in tables

        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(findings)").fetchall()
        }
        assert "blt_issue_id" in columns

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
