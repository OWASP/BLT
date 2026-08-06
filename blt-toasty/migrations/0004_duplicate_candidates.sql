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
    detection_method TEXT NOT NULL CHECK(detection_method IN ('retrieval_only', 'retrieval_plus_llm', 'llm_rejected')),
    gitlab_note_posted INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (similarity_score >= 0.0 AND similarity_score <= 1.0),
    CHECK (llm_confidence IS NULL OR (llm_confidence >= 0.0 AND llm_confidence <= 1.0))
);

CREATE INDEX IF NOT EXISTS idx_dup_candidates_candidate_id
    ON duplicate_candidates(candidate_event_id);

-- Uniqueness constraint: a given (event, candidate) pair may only be stored
-- once. Upserts (INSERT OR REPLACE) use this to overwrite existing records,
-- making duplicate detection retries idempotent at the database level.
CREATE UNIQUE INDEX IF NOT EXISTS idx_dup_candidates_unique_pair
    ON duplicate_candidates(triage_event_id, candidate_event_id);
