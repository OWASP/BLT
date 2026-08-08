-- Migration: 0005_rationale.sql
-- Creates the triage_rationale table for the Label Rationale API (Issue #10).
--
-- Every triage decision (CWE classification, duplicate flag) must be accompanied
-- by a machine-readable rationale that carries:
--   * CWE evidence snippets extracted from redacted_text ONLY
--   * A duplicate detection rationale (if a duplicate was flagged)
--   * A per-component confidence trace (geometric mean → overall_triage_confidence)
--
-- The triage_event_id column is UNIQUE, enforcing exactly one rationale row per
-- event. store_rationale() uses INSERT OR REPLACE with id = triage_event_id so
-- retries are idempotent without creating phantom rows.
--
-- The audit_completeness_check() gate queries this table (alongside
-- triage_summaries and redaction_audit) before allowing MCP export.
-- If this row is absent the export is blocked with HTTP 424 Failed Dependency.

CREATE TABLE IF NOT EXISTS triage_rationale (
    id                  TEXT    PRIMARY KEY,
    triage_event_id     TEXT    NOT NULL UNIQUE REFERENCES triage_events(id) ON DELETE CASCADE,
    cwe_rationale       TEXT    NOT NULL,   -- JSON array of CWERationale objects
    duplicate_rationale TEXT,               -- JSON object or NULL (no duplicate found)
    confidence_trace    TEXT    NOT NULL,   -- JSON object of ConfidenceTrace
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- No separate index needed: UNIQUE on triage_event_id creates one implicitly.
