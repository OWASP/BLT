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
            self._db.insert_sql = self._sql
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
        self.insert_sql = None

    def prepare(self, sql):
        return FakeStatement(self, sql)


@pytest.mark.asyncio
async def test_create_bug_rejects_forbidden_fields(monkeypatch):
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

    assert getattr(response, "status", None) == 400
    payload = json.loads(response.body)
    assert payload["error"] is True
    assert "The following fields are not allowed" in payload["message"]
    assert "verified" in payload["message"]
    assert "views" in payload["message"]
    assert fake_db.insert_params is None


@pytest.mark.asyncio
async def test_create_bug_uses_allowlist_and_server_defaults(monkeypatch):
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
        }
    )

    response = await bugs_handler.handle_bugs(
        request=MockRequest(request_body, headers={"CF-Connecting-IP": "8.8.8.8"}),
        env=MockEnv(),
        path_params={},
        query_params={},
        path="/bugs",
    )

    status = response.get("status") if isinstance(response, dict) else getattr(response, "status", None)
    assert status == 201
    
    payload = response.get("data") if isinstance(response, dict) else json.loads(response.body)
    assert payload["success"] is True

    assert fake_db.insert_params is not None

    # Extract the columns from the dynamically generated SQL query
    import re
    match = re.search(r"INSERT INTO bugs \((.*?)\)", fake_db.insert_sql)
    assert match is not None
    columns = [col.strip() for col in match.group(1).split(",")]
    
    # Map the columns to the bind parameters
    inserted_data = dict(zip(columns, fake_db.insert_params))

    # Server-managed defaults are enforced, regardless of user input.
    assert inserted_data.get("views") == 0
    assert inserted_data.get("verified") == 0
    assert inserted_data.get("score") == 10  # allowlisted
    assert inserted_data.get("status") == "open"
    assert inserted_data.get("is_hidden") == 0
    assert inserted_data.get("rewarded") == 0
    assert inserted_data.get("reporter_ip_address") == "8.8.8.8"
    assert inserted_data.get("domain") == 3  # allowlisted
    assert "user" not in inserted_data  # omitted entirely
    assert "closed_by" not in inserted_data  # omitted entirely


@pytest.mark.asyncio
async def test_create_bug_rejects_non_string_url(monkeypatch):
    fake_db = FakeDB()

    async def _fake_get_db_safe(_env):
        return fake_db

    monkeypatch.setattr(bugs_handler, "get_db_safe", _fake_get_db_safe)

    request_body = json.dumps(
        {
            "url": 123,
            "description": "test",
        }
    )

    response = await bugs_handler.handle_bugs(
        request=MockRequest(request_body, headers={"CF-Connecting-IP": "8.8.8.8"}),
        env=MockEnv(),
        path_params={},
        query_params={},
        path="/bugs",
    )

    assert getattr(response, "status", None) == 400
    payload = json.loads(response.body)
    assert payload["error"] is True
    assert payload["message"] == "URL must be a string"
    assert fake_db.insert_params is None


@pytest.mark.asyncio
async def test_create_bug_rejects_blank_url(monkeypatch):
    fake_db = FakeDB()

    async def _fake_get_db_safe(_env):
        return fake_db

    monkeypatch.setattr(bugs_handler, "get_db_safe", _fake_get_db_safe)

    request_body = json.dumps(
        {
            "url": "   ",
            "description": "test",
        }
    )

    response = await bugs_handler.handle_bugs(
        request=MockRequest(request_body, headers={"CF-Connecting-IP": "8.8.8.8"}),
        env=MockEnv(),
        path_params={},
        query_params={},
        path="/bugs",
    )

    assert getattr(response, "status", None) == 400
    payload = json.loads(response.body)
    assert payload["error"] is True
    assert payload["message"] == "URL is required"
    assert fake_db.insert_params is None


@pytest.mark.asyncio
async def test_create_bug_rejects_non_string_description(monkeypatch):
    fake_db = FakeDB()

    async def _fake_get_db_safe(_env):
        return fake_db

    monkeypatch.setattr(bugs_handler, "get_db_safe", _fake_get_db_safe)

    request_body = json.dumps(
        {
            "url": "https://example.com/vuln",
            "description": 123,
        }
    )

    response = await bugs_handler.handle_bugs(
        request=MockRequest(request_body, headers={"CF-Connecting-IP": "8.8.8.8"}),
        env=MockEnv(),
        path_params={},
        query_params={},
        path="/bugs",
    )

    assert getattr(response, "status", None) == 400
    payload = json.loads(response.body)
    assert payload["error"] is True
    assert payload["message"] == "Description must be a string"
    assert fake_db.insert_params is None


@pytest.mark.asyncio
async def test_create_bug_rejects_blank_description(monkeypatch):
    fake_db = FakeDB()

    async def _fake_get_db_safe(_env):
        return fake_db

    monkeypatch.setattr(bugs_handler, "get_db_safe", _fake_get_db_safe)

    request_body = json.dumps(
        {
            "url": "https://example.com/vuln",
            "description": "   ",
        }
    )

    response = await bugs_handler.handle_bugs(
        request=MockRequest(request_body, headers={"CF-Connecting-IP": "8.8.8.8"}),
        env=MockEnv(),
        path_params={},
        query_params={},
        path="/bugs",
    )

    assert getattr(response, "status", None) == 400
    payload = json.loads(response.body)
    assert payload["error"] is True
    assert payload["message"] == "Description is required"
    assert fake_db.insert_params is None
