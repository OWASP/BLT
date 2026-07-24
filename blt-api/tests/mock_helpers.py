"""
Shared mock infrastructure for BLT API unit tests.
"""

import sys
import json
from unittest.mock import MagicMock

class _MockResponse:
    def __init__(self, data, status=200):
        self.data = data
        self.status = status

    @classmethod
    def json(cls, data, status=200, **kwargs):
        return cls(data, status)

# Register the workers module mock
_mock_workers = MagicMock()
_mock_workers.Response = _MockResponse
sys.modules.setdefault("workers", _mock_workers)


class _AllResult:
    def __init__(self, rows):
        self.results = rows


class _FakeStatement:
    def __init__(self, db, sql):
        self._db = db
        self._sql = sql
        self._params = ()

    def bind(self, *params):
        self._params = params
        return self

    async def all(self):
        self._db._last_sql = self._sql
        self._db._last_params = self._params
        rows = self._db._all_queue.pop(0) if self._db._all_queue else self._db._default_all
        return _AllResult(rows)

    async def first(self):
        self._db._last_sql = self._sql
        self._db._last_params = self._params
        if self._db._first_queue:
            return self._db._first_queue.pop(0)
        return self._db._default_first

    async def run(self):
        self._db._last_sql = self._sql
        self._db._last_params = self._params
        self._db._run_calls.append((self._sql, self._params))


class MockDB:
    def __init__(self):
        self._last_sql = None
        self._last_params = ()
        self._run_calls = []
        self._default_all = []
        self._default_first = None
        self._all_queue = []
        self._first_queue = []

    def prepare(self, sql):
        return _FakeStatement(self, sql)

    def set_all(self, rows):
        self._default_all = rows

    def set_first(self, row):
        self._default_first = row

    def queue_all(self, *row_lists):
        self._all_queue.extend(row_lists)

    def queue_first(self, *rows):
        self._first_queue.extend(rows)


class MockRequest:
    def __init__(self, method="GET", body=None, headers=None):
        self.method = method
        self._body = body
        self.headers = headers or {}

    async def text(self):
        if self._body is None:
            return ""
        if isinstance(self._body, dict):
            return json.dumps(self._body)
        return str(self._body)


class MockEnv:
    JWT_SECRET = "test-secret-key"
