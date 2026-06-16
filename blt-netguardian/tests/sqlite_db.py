"""In-memory SQLite stand-in for D1 in integration tests."""

from __future__ import annotations

import sqlite3
from types import SimpleNamespace
from typing import Any


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


class SqliteStatement:
    def __init__(self, conn: sqlite3.Connection, sql: str):
        self.conn = conn
        self.sql = sql
        self.params: tuple[Any, ...] = ()

    def bind(self, *params: Any) -> "SqliteStatement":
        self.params = params
        return self

    async def first(self) -> dict[str, Any] | None:
        cursor = self.conn.execute(self.sql, self.params)
        row = cursor.fetchone()
        return row_to_dict(row) if row is not None else None

    async def run(self) -> dict:
        self.conn.execute(self.sql, self.params)
        self.conn.commit()
        return {}

    async def all(self) -> SimpleNamespace:
        cursor = self.conn.execute(self.sql, self.params)
        rows = [row_to_dict(row) for row in cursor.fetchall()]
        return SimpleNamespace(results=rows)


class SqliteDB:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def prepare(self, sql: str) -> SqliteStatement:
        return SqliteStatement(self.conn, sql)

    async def batch(self, statements: list[SqliteStatement]) -> list[dict]:
        results = []
        for statement in statements:
            results.append(await statement.run())
        return results


def open_ingest_db(migration_sql: str) -> SqliteDB:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(migration_sql)
    conn.commit()
    return SqliteDB(conn)
