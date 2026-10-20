"""Pytest fixtures: isolated D1 binding backed by in-memory SQLite."""

from __future__ import annotations

from pathlib import Path

import pytest_asyncio
import aiosqlite

from .mock_d1 import MockD1Binding


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def migration_files(upto: str | None = None) -> list[Path]:
    """The D1 migrations in the order wrangler applies them (by file name)."""
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    return [f for f in files if upto is None or f.name <= upto]


async def apply_migrations(conn, files: list[Path]) -> None:
    for path in files:
        await conn.executescript(path.read_text())
    await conn.commit()


@pytest_asyncio.fixture
async def db():
    """Provide a MockD1Binding backed by in-memory SQLite with every migration applied."""
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys=ON")
    await apply_migrations(conn, migration_files())

    d1 = MockD1Binding(conn)

    try:
        yield d1
    finally:
        await conn.close()
