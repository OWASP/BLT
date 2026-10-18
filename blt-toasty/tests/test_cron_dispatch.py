"""Tests for POST /__scheduled, the endpoint the blt-cron dispatcher Worker calls."""

import importlib.util
import json
import os
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")


class _Headers:
    @classmethod
    def new(cls):
        return cls()

    def set(self, key, value):
        pass


class _Response:
    def __init__(self, body, status=200, headers=None):
        self.body = body
        self.status = status

    @classmethod
    def new(cls, body, status=200, headers=None):
        return cls(body, status, headers)


def _load_worker():
    """Import src/worker.py against stubbed js/pyodide without leaking the stubs."""
    js = types.ModuleType("js")
    js.Response = _Response
    js.Headers = _Headers
    js.console = MagicMock()
    js.Object = MagicMock()
    js.Request = MagicMock()
    js.fetch = AsyncMock()
    js.__getattr__ = lambda name: MagicMock(name=f"js.{name}")  # Date, crypto, ...
    ffi = types.ModuleType("pyodide.ffi")
    ffi.to_js = lambda value, **_kw: value
    pyodide = types.ModuleType("pyodide")
    pyodide.ffi = ffi
    with patch.dict(sys.modules, {"js": js, "pyodide": pyodide, "pyodide.ffi": ffi}):
        spec = importlib.util.spec_from_file_location("toasty_worker_cron", os.path.join(_SRC, "worker.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


worker = _load_worker()


class _RequestHeaders(dict):
    def get(self, key, default=None):
        return super().get(key, default)


def _request(method="POST", secret=None, body=None):
    return types.SimpleNamespace(
        method=method,
        url="https://cron.internal/__scheduled",
        headers=_RequestHeaders({"X-BLT-Cron-Secret": secret} if secret is not None else {}),
        text=AsyncMock(return_value=json.dumps(body if body is not None else {})),
    )


async def _fetch(req, env, handler=None):
    handler = handler or AsyncMock()
    with patch.object(worker, "on_scheduled", new=handler):
        resp = await worker.on_fetch(req, env)
    return resp, handler


@pytest.mark.asyncio
async def test_missing_secret_returns_403():
    resp, handler = await _fetch(_request(), types.SimpleNamespace(CRON_SECRET="s3cret"))
    assert resp.status == 403
    handler.assert_not_called()


@pytest.mark.asyncio
async def test_wrong_secret_returns_403():
    resp, handler = await _fetch(_request(secret="nope"), types.SimpleNamespace(CRON_SECRET="s3cret"))
    assert resp.status == 403
    handler.assert_not_called()


@pytest.mark.asyncio
async def test_unset_cron_secret_refuses():
    resp, handler = await _fetch(_request(secret=""), types.SimpleNamespace())
    assert resp.status == 403
    handler.assert_not_called()


@pytest.mark.asyncio
async def test_get_returns_405():
    resp, handler = await _fetch(_request(method="GET", secret="s3cret"), types.SimpleNamespace(CRON_SECRET="s3cret"))
    assert resp.status == 405
    handler.assert_not_called()


@pytest.mark.asyncio
async def test_valid_request_runs_scheduled_handler():
    env = types.SimpleNamespace(CRON_SECRET="s3cret")
    req = _request(secret="s3cret", body={"cron": "0 * * * *", "scheduledTime": 1760227200000})
    resp, handler = await _fetch(req, env)
    assert resp.status == 200
    assert json.loads(resp.body) == {"ok": True}
    handler.assert_awaited_once()
    event, called_env, _ctx = handler.await_args.args
    assert called_env is env
    assert event.cron == "0 * * * *"
    assert event.scheduledTime == 1760227200000
    assert event.type == "scheduled"


@pytest.mark.asyncio
async def test_handler_exception_returns_500():
    env = types.SimpleNamespace(CRON_SECRET="s3cret")
    req = _request(secret="s3cret", body={"cron": "0 * * * *", "scheduledTime": 1})
    resp, _ = await _fetch(req, env, handler=AsyncMock(side_effect=RuntimeError("boom")))
    assert resp.status == 500
    body = json.loads(resp.body)
    assert body["ok"] is False
    assert "boom" in body["error"]
