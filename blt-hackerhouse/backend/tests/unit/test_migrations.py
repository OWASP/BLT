"""Migration 003: 'forge' in the events and identity_mappings CHECK constraints."""

from __future__ import annotations

import sqlite3

import aiosqlite
import pytest

from .conftest import MIGRATIONS_DIR, apply_migrations, migration_files


EXPECTED_INDEXES = {
    "idx_events_contributor",
    "idx_events_timestamp",
    "idx_events_sequence",
    "idx_identity_mappings_contributor",
    "idx_contributors_linked",
    "idx_avatar_state_room",
    "idx_dlq_source",
    "idx_dlq_created",
}


async def _indexes(conn) -> set[str]:
    rows = await (await conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_autoindex%'"
    )).fetchall()
    return {r[0] for r in rows}


@pytest.fixture
async def before_003():
    conn = await aiosqlite.connect(":memory:")
    await conn.execute("PRAGMA foreign_keys=ON")
    await apply_migrations(conn, migration_files(upto="002_zzz"))
    yield conn
    await conn.close()


async def test_order_puts_003_last():
    assert [f.name for f in migration_files()][-1] == "003_forge_source.sql"
    assert (MIGRATIONS_DIR / "003_forge_source.sql").exists()


async def test_003_keeps_rows_and_indexes_and_allows_forge(before_003):
    conn = before_003
    with pytest.raises(sqlite3.IntegrityError):
        await conn.execute(
            "INSERT INTO events (id, source, event_type, actor_id, actor_name, timestamp, idempotency_key)"
            " VALUES ('e0', 'forge', 'commit_pushed', 'a', 'a', '2026-10-19T00:00:00', 'k0')"
        )
    await conn.execute("INSERT INTO contributors (id, display_name) VALUES ('c1', 'alice')")
    await conn.execute(
        "INSERT INTO events (id, source, event_type, actor_id, actor_name, contributor_id, timestamp,"
        " metadata, idempotency_key, sequence_number)"
        " VALUES ('e1', 'gitlab', 'mr_merged', '9', 'alice', 'c1', '2026-10-19T00:00:00', '{\"x\":1}', 'k1', 7)"
    )
    await conn.execute(
        "INSERT INTO identity_mappings (platform, platform_user_id, contributor_id, confidence)"
        " VALUES ('gitlab', '9', 'c1', 1.0)"
    )
    await conn.commit()
    indexes_before = await _indexes(conn)

    await apply_migrations(conn, [MIGRATIONS_DIR / "003_forge_source.sql"])

    assert await _indexes(conn) == indexes_before
    assert EXPECTED_INDEXES <= indexes_before
    row = await (await conn.execute(
        "SELECT source, contributor_id, metadata, idempotency_key, sequence_number FROM events WHERE id = 'e1'"
    )).fetchone()
    assert tuple(row) == ("gitlab", "c1", '{"x":1}', "k1", 7)
    mapping = await (await conn.execute(
        "SELECT id, platform, platform_user_id, contributor_id FROM identity_mappings"
    )).fetchone()
    assert tuple(mapping) == (1, "gitlab", "9", "c1")

    await conn.execute(
        "INSERT INTO events (id, source, event_type, actor_id, actor_name, timestamp, idempotency_key)"
        " VALUES ('e2', 'forge', 'commit_pushed', 'bob', 'bob', '2026-10-19T00:00:00', 'forge:commit_pushed:abc')"
    )
    await conn.execute(
        "INSERT INTO identity_mappings (platform, platform_user_id, contributor_id, confidence)"
        " VALUES ('forge', 'bob', 'c1', 0.0)"
    )
    ids = [r[0] for r in await (await conn.execute("SELECT id FROM identity_mappings ORDER BY id")).fetchall()]
    assert ids == [1, 2]  # AUTOINCREMENT carries on after the rebuild

    with pytest.raises(sqlite3.IntegrityError):
        await conn.execute(
            "INSERT INTO events (id, source, event_type, actor_id, actor_name, timestamp, idempotency_key)"
            " VALUES ('e3', 'github', 'push', 'x', 'x', '2026-10-19T00:00:00', 'k3')"
        )
    with pytest.raises(sqlite3.IntegrityError):  # the unique idempotency key survived
        await conn.execute(
            "INSERT INTO events (id, source, event_type, actor_id, actor_name, timestamp, idempotency_key)"
            " VALUES ('e4', 'forge', 'commit_pushed', 'bob', 'bob', '2026-10-19T00:00:00', 'forge:commit_pushed:abc')"
        )
    with pytest.raises(sqlite3.IntegrityError):  # the unique (platform, user) pair survived
        await conn.execute(
            "INSERT INTO identity_mappings (platform, platform_user_id, contributor_id, confidence)"
            " VALUES ('forge', 'bob', 'c1', 0.5)"
        )
    with pytest.raises(sqlite3.IntegrityError):  # the contributor foreign key survived
        await conn.execute(
            "INSERT INTO events (id, source, event_type, actor_id, actor_name, contributor_id, timestamp,"
            " idempotency_key) VALUES ('e5', 'forge', 'commit_pushed', 'z', 'z', 'nobody', '2026-10-19', 'k5')"
        )
    fk = await (await conn.execute("PRAGMA foreign_key_check")).fetchall()
    assert fk == []
