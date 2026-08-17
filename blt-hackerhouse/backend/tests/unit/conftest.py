"""Pytest fixtures: isolated D1 binding backed by in-memory SQLite."""

from __future__ import annotations

import pytest_asyncio
import aiosqlite

from .mock_d1 import MockD1Binding


MIGRATION_SQL = """
PRAGMA foreign_keys = ON;

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

CREATE TABLE IF NOT EXISTS avatar_state (
    contributor_id TEXT    PRIMARY KEY REFERENCES contributors(id) ON DELETE CASCADE,
    floor          INTEGER NOT NULL CHECK(floor BETWEEN 1 AND 3),
    room           TEXT    NOT NULL,
    last_event     TEXT    NOT NULL,
    updated_at     TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

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

CREATE TABLE IF NOT EXISTS poll_cursors (
    source         TEXT    PRIMARY KEY,
    last_seen_id   INTEGER NOT NULL DEFAULT 0,
    last_polled_at TEXT,
    metadata       TEXT    NOT NULL DEFAULT '{}'
);

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

CREATE TABLE IF NOT EXISTS health_state (
    component TEXT NOT NULL,
    field     TEXT NOT NULL,
    value     TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (component, field)
);
"""


@pytest_asyncio.fixture
async def db():
    """Provide a MockD1Binding backed by in-memory SQLite with full schema."""
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys=ON")
    await conn.executescript(MIGRATION_SQL)
    await conn.commit()

    d1 = MockD1Binding(conn)

    try:
        yield d1
    finally:
        await conn.close()
