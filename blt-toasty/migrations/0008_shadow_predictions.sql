-- Migration: 0008_shadow_predictions.sql
-- Creates the shadow_predictions table for shadow mode validation.
-- Each row stores a Toasty prediction alongside the actual maintainer decision.

CREATE TABLE IF NOT EXISTS shadow_predictions (
    id TEXT PRIMARY KEY,
    gitlab_issue_url TEXT NOT NULL,
    project_id INTEGER NOT NULL,
    issue_iid INTEGER NOT NULL,
    predicted_cwe TEXT,              -- JSON array of predicted CWE strings
    predicted_duplicate_of TEXT,     -- event_id of top duplicate candidate (or NULL)
    predicted_confidence REAL,       -- summarizer confidence score
    actual_labels TEXT,              -- JSON array of labels from GitLab at comparison time
    actual_state TEXT,               -- 'closed', 'opened', etc.
    matched INTEGER DEFAULT NULL,    -- 1 = prediction matched, 0 = mismatch, NULL = not yet compared
    shadow_event_id TEXT,            -- triage_event_id created during shadow run
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    compared_at TEXT,                -- timestamp of when comparison was performed
    UNIQUE(project_id, issue_iid)
);

CREATE INDEX IF NOT EXISTS idx_shadow_predictions_created
    ON shadow_predictions(created_at);

CREATE INDEX IF NOT EXISTS idx_shadow_predictions_project
    ON shadow_predictions(project_id);
