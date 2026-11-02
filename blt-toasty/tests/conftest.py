import sys
import os
import importlib
import json
import glob
import pytest
from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# Fix the dual-module problem:  tests do `from src.errors import X` while
# source code does `from errors import X`.  Without this, Python loads two
# separate module objects and `pytest.raises` / `mock.patch` break.
#
# Solution: for every .py file in src/, ensure that both `src.<name>` and
# `<name>` point to the **same** module object in sys.modules.
# ---------------------------------------------------------------------------
_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)
_src_dir = os.path.join(_root_dir, "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

# Ensure `src` package is importable
import src as _src_pkg  # noqa: E402

for _fname in os.listdir(_src_dir):
    if _fname.endswith(".py") and _fname != "__init__.py":
        _mod_name = _fname[:-3]
        _src_mod_name = f"src.{_mod_name}"
        # If the bare module is already loaded, alias it
        if _mod_name in sys.modules and _src_mod_name not in sys.modules:
            sys.modules[_src_mod_name] = sys.modules[_mod_name]
            setattr(_src_pkg, _mod_name, sys.modules[_mod_name])
        # If the src.module is already loaded, alias the bare name
        elif _src_mod_name in sys.modules and _mod_name not in sys.modules:
            sys.modules[_mod_name] = sys.modules[_src_mod_name]
        # If neither is loaded yet, import the bare one and alias it
        elif _mod_name not in sys.modules and _src_mod_name not in sys.modules:
            try:
                _mod = importlib.import_module(_mod_name)
                sys.modules[_src_mod_name] = _mod
                setattr(_src_pkg, _mod_name, _mod)
            except Exception:
                pass  # some modules may fail to import outside Workers (e.g. js imports)


@pytest.fixture(scope="session")
def all_golden_reports():
    """
    Loads all JSON reports from both the historical and synthetic golden set directories.
    Returns a list of dictionaries.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    synthetic_files = glob.glob(os.path.join(base_dir, "golden_set", "synthetic", "*.json"))
    historical_files = glob.glob(os.path.join(base_dir, "golden_set", "historical", "*.json"))

    all_files = synthetic_files + historical_files
    reports = []

    for fpath in all_files:
        with open(fpath, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                # Store the file path in the dict for easier debugging if a test fails
                data["_filepath"] = fpath
                reports.append(data)
            except json.JSONDecodeError as e:
                pytest.fail(f"Failed to parse JSON in {fpath}: {str(e)}")

    return reports


def pytest_generate_tests(metafunc):
    """
    This tells Pytest to dynamically generate a test for EACH report in the golden set.
    Instead of running one big test 50 times, it creates 50 separate test cases.
    """
    if "golden_report" in metafunc.fixturenames:
        # We need to manually load the files here to parameterize the tests
        base_dir = os.path.dirname(os.path.abspath(__file__))
        synthetic_files = glob.glob(os.path.join(base_dir, "golden_set", "synthetic", "*.json"))
        historical_files = glob.glob(os.path.join(base_dir, "golden_set", "historical", "*.json"))
        all_files = synthetic_files + historical_files

        reports = []
        ids = []
        for fpath in all_files:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["_filepath"] = fpath
                reports.append(data)
                # Use the file name as the test ID
                ids.append(os.path.basename(fpath))

        metafunc.parametrize("golden_report", reports, ids=ids)


@pytest.fixture
def mock_d1():
    db = MagicMock()
    # Support traditional prepare().bind().run()
    db.prepare.return_value.bind.return_value.run = AsyncMock()
    db.prepare.return_value.bind.return_value.first = AsyncMock()
    # Mock db.batch()
    db.batch = AsyncMock()
    return db


@pytest.fixture
def mock_analytics():
    analytics = MagicMock()
    analytics.writeDataPoint = MagicMock()
    return analytics


class SQLiteD1:
    """In-memory stand-in for a Cloudflare D1 binding, backed by real SQLite.

    Applies the project's migrations, then runs every statement for real, so
    tests assert on query results and table contents instead of matching SQL
    text.  Supports the subset of the D1 API the Worker uses:
    ``prepare(sql).bind(*args)`` with ``first()``, ``run()`` and ``all()``,
    plus ``batch()``.  ``statements`` records each executed SQL string.
    """

    class _Meta:
        def __init__(self, changes):
            self.changes = changes

    class _Result:
        def __init__(self, changes=0, results=None):
            self.meta = SQLiteD1._Meta(changes)
            self.results = results or []

    class _Statement:
        def __init__(self, db, sql, args=()):
            self._db, self.sql, self.args = db, sql, args

        def bind(self, *args):
            return SQLiteD1._Statement(self._db, self.sql, args)

        def _execute(self):
            self._db.statements.append(self.sql)
            return self._db.conn.execute(self.sql, self.args)

        async def first(self):
            row = self._execute().fetchone()
            return dict(row) if row is not None else None

        async def all(self):
            return SQLiteD1._Result(results=[dict(r) for r in self._execute().fetchall()])

        async def run(self):
            return SQLiteD1._Result(changes=self._execute().rowcount)

    def __init__(self):
        import sqlite3

        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.statements = []
        migrations = os.path.join(_root_dir, "migrations")
        for name in sorted(f for f in os.listdir(migrations) if f[:4].isdigit() and f.endswith(".sql")):
            with open(os.path.join(migrations, name), encoding="utf-8") as fh:
                self.conn.executescript(fh.read())

    def prepare(self, sql):
        return SQLiteD1._Statement(self, sql)

    async def batch(self, statements):
        return [await s.run() for s in statements]

    def add_event(self, event_id, *, issue_iid=35, status="pending", quarantine_reason=None):
        self.conn.execute(
            "INSERT INTO triage_events (id, delivery_id, gitlab_event, project_id, issue_iid, raw_payload_hash, "
            "status, quarantine_reason) VALUES (?, ?, 'Issue Hook', 1, ?, 'hash', ?, ?)",
            (event_id, f"delivery-{event_id}", issue_iid, status, quarantine_reason),
        )

    def add_summary(self, event_id, *, cwe_hints="[]", executive_summary="summary", reviewer_pack=None):
        self.conn.execute(
            "INSERT INTO triage_summaries (id, triage_event_id, executive_summary, reviewer_pack, cwe_hints, "
            "model_used) VALUES (?, ?, ?, ?, ?, 'test-model')",
            (f"sum-{event_id}", event_id, executive_summary, reviewer_pack, cwe_hints),
        )


@pytest.fixture
def sqlite_d1():
    """A fresh SQLite-backed D1 with all migrations applied."""
    return SQLiteD1()
