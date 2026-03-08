"""Security-focused tests for bug creation handler."""

import json
import pytest

from handlers import bugs as bugs_handler


class MockRequest:
    def __init__(self, body, method="POST", headers=None):
        self.method = method
        self._body = body
        self.headers = headers or {}

    async def text(self):
        return self._body


class MockEnv:
    pass


@pytest.mark.asyncio
async def test_create_bug_uses_allowlist_and_server_defaults(monkeypatch):
    class FakeStatement:
        def __init__(self, db, sql):
            self._db = db
            self._sql = sql
            self._params = ()

        def bind(self, *params):
            self._params = params
            return self

        async def run(self):
            if "INSERT INTO bugs" in self._sql:
                self._db.insert_params = self._params
            return None

        async def first(self):
            if "last_insert_rowid()" in self._sql:
                return {"id": 1}
            if "SELECT * FROM bugs WHERE id = ?" in self._sql:
                return {"id": 1, "url": "https://example.com/vuln", "description": "test"}
            return None

    class FakeDB:
        def __init__(self):
            self.insert_params = None

        def prepare(self, sql):
            return FakeStatement(self, sql)

    fake_db = FakeDB()

    async def _fake_get_db_safe(_env):
        return fake_db

    monkeypatch.setattr(bugs_handler, "get_db_safe", _fake_get_db_safe)

    request_body = json.dumps(
        {
            "url": "https://example.com/vuln",
            "description": "test",
            "score": 10,
            "domain": 3,
            "verified": True,
            "user": 10,
            "closed_by": 20,
            "reporter_ip_address": "1.2.3.4",
            "views": 999,
            "status": "closed",
            "is_hidden": 1,
            "rewarded": 123,
        }
    )

    response = await bugs_handler.handle_bugs(
        request=MockRequest(request_body, headers={"CF-Connecting-IP": "8.8.8.8"}),
        env=MockEnv(),
        path_params={},
        query_params={},
        path="/bugs",
    )

    assert getattr(response, "status", None) == 201
    payload = json.loads(response.body)
    assert payload["success"] is True

    assert fake_db.insert_params is not None

    # Server-managed defaults are enforced, regardless of user input.
    assert fake_db.insert_params[4] == 0  # views
    assert fake_db.insert_params[5] == 0  # verified
    assert fake_db.insert_params[6] == 10  # score (allowlisted)
    assert fake_db.insert_params[7] == "open"  # status
    assert fake_db.insert_params[12] == 0  # is_hidden
    assert fake_db.insert_params[13] == 0  # rewarded
    assert fake_db.insert_params[14] == "8.8.8.8"  # reporter_ip_address
    assert fake_db.insert_params[18] == 3  # domain (allowlisted)
    assert fake_db.insert_params[19] is None  # user (no auth user in request)
    assert fake_db.insert_params[20] is None  # closed_by
