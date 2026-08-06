-- Migration: 0003_embedded_pending.sql
-- Extends triage_events CHECK constraint to include 'embedded_pending',
-- supporting graceful degradation when the FastEmbed sidecar is unavailable.
--
-- Pipeline states after this migration:
--   pending → redaction_passed → summarized → embedded → exported
--                                    ↓
--                            embedded_pending → embedded
--                                    ↓
--                               quarantined
--
-- D1 (SQLite) does not support ALTER TABLE … MODIFY CONSTRAINT.
-- We rebuild the table using the standard SQLite rename-and-recreate pattern,
-- copy all existing rows (quarantine_reason defaults to NULL for old rows),
-- and restore every original index so existing queries remain intact.

BEGIN TRANSACTION;
PRAGMA defer_foreign_keys = TRUE;

-- Step 1: Create new table with the expanded CHECK constraint.
CREATE TABLE triage_events_new (
    id                TEXT    PRIMARY KEY,
    delivery_id       TEXT    UNIQUE NOT NULL,
    gitlab_event      TEXT    NOT NULL,
    project_id        INTEGER NOT NULL,
    issue_iid         INTEGER,
    raw_payload_hash  TEXT    NOT NULL,
    status            TEXT    NOT NULL DEFAULT 'pending'
                      CHECK(status IN (
                          'pending',
                          'redaction_passed',
                          'redaction_failed',
                          'summarized',
                          'embedded',
                          'embedded_pending',
                          'exported',
                          'quarantined'
                      )),
    quarantine_reason TEXT,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Step 2: Copy all existing rows; quarantine_reason defaults to NULL.
INSERT INTO triage_events_new
    (id, delivery_id, gitlab_event, project_id, issue_iid,
     raw_payload_hash, status, created_at, updated_at)
SELECT
    id, delivery_id, gitlab_event, project_id, issue_iid,
    raw_payload_hash, status, created_at, updated_at
FROM triage_events;

-- Step 3: Replace the old table.
DROP TABLE triage_events;
ALTER TABLE triage_events_new RENAME TO triage_events;

-- Step 4: Restore all indexes that 0001_initial.sql originally created.
CREATE INDEX IF NOT EXISTS idx_triage_events_status
    ON triage_events(status);
CREATE INDEX IF NOT EXISTS idx_triage_events_delivery
    ON triage_events(delivery_id);

COMMIT;
