-- BLT Ketchup — D1 (SQLite) Schema
-- Apply with: wrangler d1 execute blt-ketchup-db --file=schema.sql

-- Workspace = one red-team engagement
CREATE TABLE IF NOT EXISTS workspaces (
    id          TEXT PRIMARY KEY,           -- e.g. ws_AbCd1234
    name        TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active'   -- active | in_review | completed | archived
                    CHECK (status IN ('active','in_review','completed','archived')),
    owner_id    TEXT NOT NULL,
    created_at  INTEGER NOT NULL            -- Unix timestamp
);

-- Team membership
CREATE TABLE IF NOT EXISTS memberships (
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id      TEXT NOT NULL,
    role         TEXT NOT NULL DEFAULT 'contributor'
                    CHECK (role IN ('owner','lead','contributor','viewer')),
    joined_at    INTEGER NOT NULL DEFAULT (unixepoch()),
    PRIMARY KEY (workspace_id, user_id)
);

-- Finding metadata (bodies are encrypted in KV)
CREATE TABLE IF NOT EXISTS findings (
    id           TEXT PRIMARY KEY,          -- e.g. fnd_XyZw5678
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    title        TEXT NOT NULL,
    severity     TEXT NOT NULL
                    CHECK (severity IN ('CRITICAL','HIGH','MEDIUM','LOW','INFORMATIONAL')),
    cvss_score   REAL NOT NULL DEFAULT 0.0,
    status       TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open','in_progress','needs_review','resolved','accepted_risk','escalated')),
    assigned_to  TEXT,                      -- user_id
    created_by   TEXT NOT NULL,             -- user_id
    created_at   INTEGER NOT NULL           -- Unix timestamp
);

-- Evidence metadata (file bytes are encrypted in KV)
CREATE TABLE IF NOT EXISTS evidence (
    id           TEXT PRIMARY KEY,          -- e.g. ev_MnOp9012
    finding_id   TEXT NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL,
    filename     TEXT NOT NULL,
    size_bytes   INTEGER NOT NULL,
    uploaded_by  TEXT NOT NULL,
    uploaded_at  INTEGER NOT NULL
);

-- Escalation log
CREATE TABLE IF NOT EXISTS escalations (
    id               TEXT PRIMARY KEY,
    finding_id       TEXT NOT NULL REFERENCES findings(id),
    workspace_id     TEXT NOT NULL,
    disclosure_type  TEXT NOT NULL CHECK (disclosure_type IN ('public','coordinated','private')),
    blt_url          TEXT,
    submitted_by     TEXT NOT NULL,
    submitted_at     INTEGER NOT NULL
);

-- Audit log (immutable append-only)
CREATE TABLE IF NOT EXISTS audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id TEXT NOT NULL,
    actor_id     TEXT NOT NULL,
    action       TEXT NOT NULL,
    target_type  TEXT,
    target_id    TEXT,
    meta         TEXT,                      -- JSON blob
    occurred_at  INTEGER NOT NULL DEFAULT (unixepoch())
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_findings_workspace  ON findings(workspace_id);
CREATE INDEX IF NOT EXISTS idx_findings_severity   ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_status     ON findings(status);
CREATE INDEX IF NOT EXISTS idx_memberships_user    ON memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_evidence_finding    ON evidence(finding_id);
CREATE INDEX IF NOT EXISTS idx_audit_workspace     ON audit_log(workspace_id);