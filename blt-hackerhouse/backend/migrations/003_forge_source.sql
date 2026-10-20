-- Migration 003: allow 'forge' (git.owaspblt.org) as an event source and identity platform.
--
-- SQLite cannot alter a CHECK constraint, so events and identity_mappings are rebuilt:
-- create the new table, copy every row, drop the old table, rename, recreate the indexes.
-- Nothing references either table, so dropping them does not touch other rows.
-- Cost: one row written per existing row plus its index entries (the tables were empty
-- when this was written, so it is close to zero on D1).

PRAGMA defer_foreign_keys = on;

-- events ---------------------------------------------------------------------
CREATE TABLE events_new (
    id              TEXT    PRIMARY KEY,
    source          TEXT    NOT NULL CHECK(source IN ('gitlab', 'blt', 'forge')),
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

INSERT INTO events_new (
    id, source, event_type, actor_id, actor_name, contributor_id, repository,
    timestamp, metadata, idempotency_key, sequence_number, created_at
)
SELECT
    id, source, event_type, actor_id, actor_name, contributor_id, repository,
    timestamp, metadata, idempotency_key, sequence_number, created_at
FROM events;

DROP TABLE events;
ALTER TABLE events_new RENAME TO events;

CREATE INDEX IF NOT EXISTS idx_events_contributor ON events(contributor_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp   ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_sequence    ON events(sequence_number);

-- identity_mappings ----------------------------------------------------------
CREATE TABLE identity_mappings_new (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    platform         TEXT    NOT NULL CHECK(platform IN ('gitlab', 'blt', 'forge')),
    platform_user_id TEXT    NOT NULL,
    contributor_id   TEXT    NOT NULL REFERENCES contributors(id) ON DELETE CASCADE,
    confidence       REAL    NOT NULL CHECK(confidence BETWEEN 0.0 AND 1.0),
    confirmed_by     TEXT,
    created_at       TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(platform, platform_user_id)
);

INSERT INTO identity_mappings_new (
    id, platform, platform_user_id, contributor_id, confidence, confirmed_by, created_at
)
SELECT
    id, platform, platform_user_id, contributor_id, confidence, confirmed_by, created_at
FROM identity_mappings;

DROP TABLE identity_mappings;
ALTER TABLE identity_mappings_new RENAME TO identity_mappings;

CREATE INDEX IF NOT EXISTS idx_identity_mappings_contributor ON identity_mappings(contributor_id);
