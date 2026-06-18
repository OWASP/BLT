-- Migration 001: Initial schema for BLT-Hackerhouse
-- Implements VF09: SQLite Schema (6 tables per MVP_V1_SPEC.md)

PRAGMA foreign_keys = ON;

-- Events table (VF09)
CREATE TABLE IF NOT EXISTS events (
    id              TEXT    PRIMARY KEY,
    source          TEXT    NOT NULL CHECK(source IN ('gitlab', 'blt')),
    event_type      TEXT    NOT NULL,
    actor_id        TEXT    NOT NULL,
    actor_name      TEXT    NOT NULL,
    contributor_id  TEXT    REFERENCES contributors(id),
    repository      TEXT    NOT NULL DEFAULT '',
    timestamp       TEXT    NOT NULL,
    metadata        TEXT    NOT NULL DEFAULT '{}',
    idempotency_key TEXT    UNIQUE NOT NULL,
    sequence_number INTEGER,
    created_at      TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_idempotency ON events(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_events_contributor ON events(contributor_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp   ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_sequence    ON events(sequence_number);

-- Contributors table (VF09)
CREATE TABLE IF NOT EXISTS contributors (
    id            TEXT    PRIMARY KEY,
    display_name  TEXT    NOT NULL,
    usernames     TEXT    NOT NULL DEFAULT '[]',
    aliases       TEXT    NOT NULL DEFAULT '[]',
    platform_ids  TEXT    NOT NULL DEFAULT '{}',
    is_linked     INTEGER NOT NULL DEFAULT 0,
    score         INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_contributors_linked ON contributors(is_linked);

-- Avatar state table (VF09)
CREATE TABLE IF NOT EXISTS avatar_state (
    contributor_id TEXT    PRIMARY KEY REFERENCES contributors(id) ON DELETE CASCADE,
    floor          INTEGER NOT NULL CHECK(floor BETWEEN 1 AND 3),
    room           TEXT    NOT NULL,
    last_event     TEXT    NOT NULL,
    updated_at     TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_avatar_state_room ON avatar_state(room);

-- Identity mappings table (VF09)
CREATE TABLE IF NOT EXISTS identity_mappings (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    platform         TEXT    NOT NULL CHECK(platform IN ('gitlab', 'blt')),
    platform_user_id TEXT    NOT NULL,
    contributor_id   TEXT    NOT NULL REFERENCES contributors(id) ON DELETE CASCADE,
    confidence       REAL    NOT NULL CHECK(confidence BETWEEN 0.0 AND 1.0),
    confirmed_by     TEXT,
    created_at       TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(platform, platform_user_id)
);

CREATE INDEX IF NOT EXISTS idx_identity_mappings_contributor ON identity_mappings(contributor_id);

-- Poll cursors table (VF09)
CREATE TABLE IF NOT EXISTS poll_cursors (
    source         TEXT    PRIMARY KEY,
    last_seen_id   INTEGER NOT NULL DEFAULT 0,
    last_polled_at TEXT,
    metadata       TEXT    NOT NULL DEFAULT '{}'
);

-- Dead letter queue table (VF09 / VF20)
CREATE TABLE IF NOT EXISTS dead_letter_queue (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id        TEXT,
    source          TEXT,
    error           TEXT    NOT NULL,
    payload         TEXT    NOT NULL DEFAULT '{}',
    attempts        INTEGER NOT NULL DEFAULT 1,
    last_attempt_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at      TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dlq_source ON dead_letter_queue(source);
CREATE INDEX IF NOT EXISTS idx_dlq_created ON dead_letter_queue(created_at);