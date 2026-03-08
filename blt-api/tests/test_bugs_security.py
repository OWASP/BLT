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
async def test_create_bug_rejects_privileged_fields(monkeypatch):
    async def _fake_get_db_safe(_env):
        return object()

    monkeypatch.setattr(bugs_handler, "get_db_safe", _fake_get_db_safe)

    request_body = json.dumps(
        {
            "url": "https://example.com/vuln",
            "description": "test",
            "verified": True,
            "user": 10,
            "closed_by": 20,
            "reporter_ip_address": "1.2.3.4",
        }
    )

    response = await bugs_handler.handle_bugs(
        request=MockRequest(request_body),
        env=MockEnv(),
        path_params={},
        query_params={},
        path="/bugs",
    )

    assert getattr(response, "status", None) == 400
    payload = json.loads(response.body)
    assert payload["error"] is True
    assert "server-managed" in payload["message"]
