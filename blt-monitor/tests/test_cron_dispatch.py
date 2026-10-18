"""Tests for POST /__scheduled, the endpoint the blt-cron dispatcher Worker calls.

worker.py imports the Cloudflare ``workers`` runtime module, which is stubbed
here.  Run with:  pip install pytest && python -m pytest tests/ -q
"""

import asyncio
import importlib.util
import json
import pathlib
import sys
import types
from unittest.mock import AsyncMock, patch

ROOT = pathlib.Path(__file__).resolve().parent.parent


class _Response:
    def __init__(self, body, status=200):
        self.body = body
        self.status = status

    @classmethod
    def json(cls, data, status=200):
        return cls(json.dumps(data), status)


class _WorkerEntrypoint:
    def __init__(self, env=None, ctx=None):
        self.env = env
        self.ctx = ctx


def _load_worker():
    workers = types.ModuleType("workers")
    workers.Response = _Response
    workers.WorkerEntrypoint = _WorkerEntrypoint
    workers.fetch = AsyncMock()
    with patch.dict(sys.modules, {"workers": workers}):
        spec = importlib.util.spec_from_file_location("monitor_worker", ROOT / "worker.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


worker = _load_worker()


class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key, default)


def _request(method="POST", secret=None, body=None):
    return types.SimpleNamespace(
        method=method,
        url="https://cron.internal/__scheduled",
        headers=_Headers({"X-BLT-Cron-Secret": secret} if secret is not None else {}),
        text=AsyncMock(return_value=json.dumps(body if body is not None else {})),
    )


def _fetch(req, env, handler=None):
    handler = handler or AsyncMock()
    entry = worker.Default(env)
    with patch.object(worker.Default, "scheduled", new=handler):
        resp = asyncio.run(entry.fetch(req))
    return resp, handler


def test_missing_secret_returns_403():
    resp, handler = _fetch(_request(), types.SimpleNamespace(CRON_SECRET="s3cret"))
    assert resp.status == 403
    handler.assert_not_called()


def test_wrong_secret_returns_403():
    resp, handler = _fetch(_request(secret="nope"), types.SimpleNamespace(CRON_SECRET="s3cret"))
    assert resp.status == 403
    handler.assert_not_called()


def test_unset_cron_secret_refuses():
    resp, handler = _fetch(_request(secret=""), types.SimpleNamespace())
    assert resp.status == 403
    handler.assert_not_called()


def test_get_returns_405():
    resp, handler = _fetch(_request(method="GET", secret="s3cret"), types.SimpleNamespace(CRON_SECRET="s3cret"))
    assert resp.status == 405
    handler.assert_not_called()


def test_valid_request_runs_scheduled_handler():
    env = types.SimpleNamespace(CRON_SECRET="s3cret")
    req = _request(secret="s3cret", body={"cron": "*/5 * * * *", "scheduledTime": 1760000700000})
    resp, handler = _fetch(req, env)
    assert resp.status == 200
    assert json.loads(resp.body) == {"ok": True}
    handler.assert_awaited_once()
    event, called_env, _ctx = handler.await_args.args
    assert called_env is env
    assert event.cron == "*/5 * * * *"
    assert event.scheduledTime == 1760000700000
    assert event.type == "scheduled"


def test_dispatched_event_selects_shard_from_scheduled_time():
    env = types.SimpleNamespace(CRON_SECRET="s3cret")
    scheduled_time = 7 * worker.SHARD_INTERVAL_MS  # shard 7 % 4 == 3
    req = _request(secret="s3cret", body={"cron": "*/5 * * * *", "scheduledTime": scheduled_time})
    entry = worker.Default(env)
    with patch.object(worker.Default, "run_monitors", new=AsyncMock(return_value=[])) as run:
        resp = asyncio.run(entry.fetch(req))
    assert resp.status == 200
    run.assert_awaited_once_with(3, env)


def test_handler_exception_returns_500():
    env = types.SimpleNamespace(CRON_SECRET="s3cret")
    req = _request(secret="s3cret", body={"cron": "*/5 * * * *", "scheduledTime": 1})
    resp, _ = _fetch(req, env, handler=AsyncMock(side_effect=RuntimeError("boom")))
    assert resp.status == 500
    body = json.loads(resp.body)
    assert body["ok"] is False
    assert "boom" in body["error"]
