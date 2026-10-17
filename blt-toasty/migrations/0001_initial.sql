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

CREATE TABLE IF NOT EXISTS redaction_audit (
    id TEXT PRIMARY KEY,
    triage_event_id TEXT NOT NULL REFERENCES triage_events(id),
    entity_type TEXT NOT NULL,
    detector TEXT NOT NULL,
    confidence REAL NOT NULL,
    byte_start INTEGER NOT NULL,
    byte_end INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prompt_versions (
    id TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rate_limits (
    agent_id TEXT PRIMARY KEY,
    request_count INTEGER NOT NULL DEFAULT 0,
    window_start TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS triage_audit_log (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES triage_events(id),
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
