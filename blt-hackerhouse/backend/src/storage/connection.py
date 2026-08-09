"""Async SQLite database connection and migration runner."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator

import aiosqlite

from ..config import settings


logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


class Database:
    """Async SQLite wrapper with WAL mode and foreign keys enabled."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else settings.database_path
        self._connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        if self._connection is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(self.path)
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute("PRAGMA journal_mode=WAL")
        await self._connection.execute("PRAGMA foreign_keys=ON")
        await self._connection.execute("PRAGMA synchronous=NORMAL")
        await self._connection.commit()
        logger.info("Database connected at %s", self.path)

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
            logger.info("Database closed")

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._connection is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._connection

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        """Context manager wrapping a BEGIN/COMMIT block."""
        try:
            await self.conn.execute("BEGIN")
            yield self.conn
            await self.conn.commit()
        except Exception:
            await self.conn.rollback()
            raise

    async def run_migrations(self) -> int:
        """Apply every *.sql file in the migrations directory in order.

        Migrations are tracked in the ``_migrations`` table to avoid
        re-running. Returns the number of migrations applied.
        """
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS _migrations (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT UNIQUE NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await self.conn.commit()

        applied_count = 0
        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            async with self.conn.execute(
                "SELECT 1 FROM _migrations WHERE name = ?", (sql_file.name,)
            ) as cursor:
                row = await cursor.fetchone()
                if row is not None:
                    continue

            logger.info("Applying migration %s", sql_file.name)
            sql_text = sql_file.read_text(encoding="utf-8")
            statements = [s.strip() for s in sql_text.split(";") if s.strip()]

            async with self.transaction():
                for stmt in statements:
                    await self.conn.execute(stmt)
                await self.conn.execute(
                    "INSERT INTO _migrations (name) VALUES (?)", (sql_file.name,)
                )

            applied_count += 1

        logger.info("Migrations complete: %d new applied", applied_count)
        return applied_count


_database: Database | None = None


def get_database() -> Database:
    """Return the process-wide Database singleton (lazy)."""
    global _database
    if _database is None:
        _database = Database()
    return _database


def reset_database() -> None:
    """Test helper — drop the singleton so a fresh instance is created."""
    global _database
    _database = None


def utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string with second precision."""
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat()


def parse_utc(value: str | datetime) -> datetime:
    """Parse an ISO 8601 string (or pass-through a datetime) into a naive UTC datetime."""
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
    text = value.replace("Z", "+00:00") if isinstance(value, str) else value
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def dumps_json(value: object) -> str:
    """Serialize Python object to compact JSON for storage."""
    return json.dumps(value, separators=(",", ":"), default=str)


def loads_json(text: str | None) -> object:
    """Deserialize JSON column, defaulting to {} or [] on empty."""
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in column, returning empty: %r", text[:80])
        return {}