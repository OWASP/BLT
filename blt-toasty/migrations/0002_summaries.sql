-- Migration: 0002_summaries.sql
-- Creates the triage_summaries table for the summarizer pipeline.
-- Each row stores the LLM-generated triage output for a single event.

CREATE TABLE IF NOT EXISTS triage_summaries (
    id TEXT PRIMARY KEY,
    triage_event_id TEXT NOT NULL REFERENCES triage_events(id),
    executive_summary TEXT NOT NULL,
    reviewer_pack TEXT,
    cwe_hints TEXT,       -- JSON array of CWE strings
    repro_steps TEXT,     -- JSON array of redacted step strings
    confidence REAL,
    model_used TEXT NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_summaries_event_id
    ON triage_summaries(triage_event_id);
