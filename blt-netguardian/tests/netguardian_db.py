"""Open in-memory D1 with all NetGuardian migrations applied."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlite_db import SqliteDB


def open_netguardian_db(repo_root: Path) -> SqliteDB:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    migrations_dir = repo_root / "migrations"
    for path in sorted(migrations_dir.glob("*.sql")):
        conn.executescript(path.read_text())
    conn.commit()
    return SqliteDB(conn)
