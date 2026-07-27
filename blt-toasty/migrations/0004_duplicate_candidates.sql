-- Migration: 0004_duplicate_candidates.sql
-- Creates the duplicate_candidates table for storing duplicate detection results.
--
-- This table records every candidate identified by the 3-tier duplicate
-- scoring pipeline in src/duplicate_detector.py:
--
--   Tier 1 (score >= 0.85): retrieval_only — accepted without LLM
--   Tier 2 (0.80 <= score < 0.85): retrieval_plus_llm — LLM adjudication
--   Tier 3 (score < 0.80): discarded (never stored)
--
-- State machine context:
--   pending → redaction_passed → summarized → embedded → exported
--                                                ↓
--                                        embedded_pending

CREATE TABLE IF NOT EXISTS duplicate_candidates (
    id TEXT PRIMARY KEY,
    triage_event_id TEXT NOT NULL REFERENCES triage_events(id),
    candidate_event_id TEXT NOT NULL,
    similarity_score REAL NOT NULL,
    llm_confirmed INTEGER DEFAULT 0,
    llm_confidence REAL,
    llm_rationale TEXT,
    detection_method TEXT NOT NULL,
    gitlab_note_posted INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_dup_candidates_event_id
    ON duplicate_candidates(triage_event_id);

CREATE INDEX IF NOT EXISTS idx_dup_candidates_candidate_id
    ON duplicate_candidates(candidate_event_id);

-- Uniqueness constraint: a given (event, candidate) pair may only be stored
-- once. Upserts (INSERT OR REPLACE) use this to overwrite existing records,
-- making duplicate detection retries idempotent at the database level.
CREATE UNIQUE INDEX IF NOT EXISTS idx_dup_candidates_unique_pair
    ON duplicate_candidates(triage_event_id, candidate_event_id);
