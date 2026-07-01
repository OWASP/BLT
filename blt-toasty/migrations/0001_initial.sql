CREATE TABLE IF NOT EXISTS triage_events (
    id TEXT PRIMARY KEY,
    delivery_id TEXT UNIQUE NOT NULL,
    gitlab_event TEXT NOT NULL,
    project_id INTEGER NOT NULL,
    issue_iid INTEGER,
    raw_payload_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending','redaction_passed','redaction_failed',
                         'summarized','embedded','exported','quarantined')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_triage_events_status ON triage_events(status);
CREATE INDEX IF NOT EXISTS idx_triage_events_delivery ON triage_events(delivery_id);
