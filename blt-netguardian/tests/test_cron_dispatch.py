"""POST /__scheduled — the endpoint the blt-cron dispatcher Worker calls."""
from pathlib import Path
import json
import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


class FakeResponse:
    """Minimal workers.Response-compatible object for tests."""

    def __init__(self, body="", status=200, headers=None):
        self.body = body
        self.status = status
        self.headers = dict(headers or {})


if "workers" not in sys.modules:
    workers_module = types.ModuleType("workers")
    workers_module.Response = FakeResponse
    sys.modules["workers"] = workers_module

import worker as worker_module  # noqa: E402


class FakeRequest:
    def __init__(self, method="POST", secret=None, payload=None):
        self.url = "https://cron.internal/__scheduled"
        self.method = method
        self.headers = {"X-BLT-Cron-Secret": secret} if secret is not None else {}
        self._body = json.dumps(payload if payload is not None else {})

    async def text(self):
        return self._body


async def _fetch(request, env, handler=None):
    handler = handler or AsyncMock()
    assets = SimpleNamespace(fetch=AsyncMock())
    env.ASSETS = assets
    with patch.object(worker_module, "on_scheduled", new=handler):
        response = await worker_module.on_fetch(request, env, "ctx")
    assets.fetch.assert_not_called()
    return response, handler


@pytest.mark.asyncio
async def test_missing_secret_returns_403():
    response, handler = await _fetch(FakeRequest(), SimpleNamespace(CRON_SECRET="s3cret"))
    assert response.status == 403
    handler.assert_not_called()


@pytest.mark.asyncio
async def test_wrong_secret_returns_403():
    response, handler = await _fetch(FakeRequest(secret="nope"), SimpleNamespace(CRON_SECRET="s3cret"))
    assert response.status == 403
    handler.assert_not_called()


@pytest.mark.asyncio
async def test_unset_cron_secret_refuses():
    response, handler = await _fetch(FakeRequest(secret=""), SimpleNamespace())
    assert response.status == 403
    handler.assert_not_called()


@pytest.mark.asyncio
async def test_get_returns_405():
    response, handler = await _fetch(FakeRequest(method="GET", secret="s3cret"), SimpleNamespace(CRON_SECRET="s3cret"))
    assert response.status == 405
    handler.assert_not_called()


@pytest.mark.asyncio
async def test_valid_request_runs_scheduled_handler():
    env = SimpleNamespace(CRON_SECRET="s3cret")
    request = FakeRequest(secret="s3cret", payload={"cron": "*/5 * * * *", "scheduledTime": 1760000700000})
    response, handler = await _fetch(request, env)
    assert response.status == 200
    assert json.loads(response.body) == {"ok": True}
    handler.assert_awaited_once()
    event, called_env, ctx = handler.await_args.args
    assert called_env is env
    assert ctx == "ctx"
    assert event.cron == "*/5 * * * *"
    assert event.scheduledTime == 1760000700000
    assert event.type == "scheduled"


@pytest.mark.asyncio
async def test_handler_exception_returns_500():
    env = SimpleNamespace(CRON_SECRET="s3cret")
    request = FakeRequest(secret="s3cret", payload={"cron": "*/5 * * * *", "scheduledTime": 1})
    response, _ = await _fetch(request, env, handler=AsyncMock(side_effect=RuntimeError("boom")))
    assert response.status == 500
    payload = json.loads(response.body)
    assert payload["ok"] is False
    assert "boom" in payload["error"]
