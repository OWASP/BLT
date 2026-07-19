"""Pytest fixtures: isolated SQLite database per test."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest_asyncio

from src.storage import Database, reset_database


@pytest_asyncio.fixture
async def db():
    """Provide a fresh on-disk SQLite database with migrations applied."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.db"
        os.environ["DATABASE_PATH"] = str(path)
        # Reset module singleton so a new Database is created per test.
        reset_database()
        from src import config as config_module
        config_module.settings.__init__()  # type: ignore[attr-defined]
        database = Database(path=path)
        await database.connect()
        await database.run_migrations()
        try:
            yield database
        finally:
            await database.close()