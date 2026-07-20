"""In-process D1 binding backed by SQLite (aiosqlite).

Provides the same API surface as a Cloudflare D1 binding so storage
tests can run without the Workers runtime.
"""

from __future__ import annotations

from typing import Any


class D1Result:
    """Wraps a single row dict to provide ``.copy()`` (D1-compatible)."""

    def __init__(self, row: dict[str, Any] | None = None) -> None:
        self._row = row or {}
        self.results: list[D1Result] | None = None

    def copy(self) -> dict[str, Any]:
        return dict(self._row)

    @staticmethod
    def from_rows(rows: list[dict[str, Any]]) -> D1Result:
        result = D1Result()
        result.results = [D1Result(r) for r in rows]
        return result


class D1Statement:
    """A prepared statement with bound parameters."""

    def __init__(self, db: MockD1Binding, sql: str, params: tuple = ()) -> None:
        self._db = db
        self._sql = sql
        self._params = params

    def bind(self, *args: Any) -> D1Statement:
        self._params = args
        return self

    async def run(self) -> D1RunResult:
        import aiosqlite
        try:
            cursor = await self._db._conn.execute(self._sql, self._params)
            await self._db._conn.commit()
            success = cursor.rowcount > 0
            return D1RunResult(success=success)
        except aiosqlite.IntegrityError:
            return D1RunResult(success=False)
        except aiosqlite.Error:
            return D1RunResult(success=False)

    async def first(self) -> D1Result | None:
        import aiosqlite
        cursor = await self._db._conn.execute(self._sql, self._params)
        row = await cursor.fetchone()
        if row is None:
            return None
        return D1Result(dict(row))

    async def all(self) -> D1Result:
        import aiosqlite
        cursor = await self._db._conn.execute(self._sql, self._params)
        rows = await cursor.fetchall()
        return D1Result.from_rows([dict(r) for r in rows])


class D1RunResult:
    def __init__(self, success: bool = True) -> None:
        self.success = success


class MockD1Binding:
    """In-process D1 binding backed by SQLite."""

    def __init__(self, conn) -> None:
        self._conn = conn

    def prepare(self, sql: str) -> D1Statement:
        return D1Statement(self, sql)
