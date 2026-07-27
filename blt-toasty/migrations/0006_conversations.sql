-- Migration 0006: Conversation archive table for Durable Objects turn archival.
--
-- Stores turns that have been evicted from the 5-turn rolling buffer
-- in ConversationDO. Each row is a single conversation turn.

CREATE TABLE IF NOT EXISTS conversation_archive (
    id TEXT PRIMARY KEY,
    triage_event_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('ai', 'developer')),
    content TEXT NOT NULL,
    turn_index INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_conversation_archive_event_turn
    ON conversation_archive (triage_event_id, turn_index);
