"""Tests for POST /__scheduled, the endpoint the blt-cron dispatcher Worker calls."""

import asyncio
import importlib.util
import json
import pathlib
import sys
import types
from unittest.mock import AsyncMock, Mock, patch

SRC = pathlib.Path(__file__).resolve().parent.parent / "src"


class _Headers:
    def __init__(self, data=None):
        self._data = dict(data or {})

    @classmethod
    def new(cls, data=None):
        return cls(data)

    def set(self, key, value):
        self._data[key] = value

    def get(self, key, default=None):
        return self._data.get(key, default)


class _Response:
    def __init__(self, body, init):
        self.body = body
        self.status = init.get("status", 200)
        self.headers = init.get("headers") or _Headers()

    @classmethod
    def new(cls, body="", init=None):
        return cls(body, init or {})


def _load_worker():
    """Import src/worker.py with the Cloudflare runtime modules stubbed."""
    js = types.ModuleType("js")
    js.Headers = _Headers
    js.Response = _Response
    js.Request = Mock()
    js.fetch = AsyncMock()

    class WorkerEntrypoint:
        env = None

    workers = types.ModuleType("workers")
    workers.WorkerEntrypoint = WorkerEntrypoint
    with patch.dict(sys.modules, {"js": js, "workers": workers}):
        if str(SRC) not in sys.path:
            sys.path.insert(0, str(SRC))
        spec = importlib.util.spec_from_file_location("lettuce_worker_cron", SRC / "worker.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


worker = _load_worker()


def _request(method="POST", secret=None, body=None):
    return types.SimpleNamespace(
        method=method,
        url="https://cron.internal/__scheduled",
        headers=_Headers({"X-BLT-Cron-Secret": secret} if secret is not None else {}),
        text=AsyncMock(return_value=json.dumps(body if body is not None else {})),
    )


def _fetch(req, env, handler=None):
    handler = handler or AsyncMock()
    entry = worker.Default()
    entry.env = env
    entry.ctx = None
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
    req = _request(secret="s3cret", body={"cron": "* * * * *", "scheduledTime": 1760000400000})
    resp, handler = _fetch(req, env)
    assert resp.status == 200
    assert json.loads(resp.body) == {"ok": True}
    handler.assert_awaited_once()
    event, called_env, _ctx = handler.await_args.args
    assert called_env is env
    assert event.cron == "* * * * *"
    assert event.scheduledTime == 1760000400000
    assert event.type == "scheduled"


def test_dispatched_event_drives_minute_staggering():
    """The real scheduled() reads controller.scheduledTime to pick jobs."""
    env = types.SimpleNamespace(CRON_SECRET="s3cret", DB=object())
    # 1760000400000 ms = 2025-10-09T09:00:00Z -> minute 0 runs both jobs.
    req = _request(secret="s3cret", body={"cron": "* * * * *", "scheduledTime": 1760000400000})
    entry = worker.Default()
    entry.env = env
    with patch.object(worker, "run_workspace_metrics_sync", new=AsyncMock()) as metrics, \
            patch.object(worker, "run_inactivity_monitor", new=AsyncMock()) as inactivity:
        resp = asyncio.run(entry.fetch(req))
    assert resp.status == 200
    metrics.assert_awaited_once_with(env)
    inactivity.assert_awaited_once_with(env)


def test_handler_exception_returns_500():
    env = types.SimpleNamespace(CRON_SECRET="s3cret")
    req = _request(secret="s3cret", body={"cron": "* * * * *", "scheduledTime": 1})
    resp, _ = _fetch(req, env, handler=AsyncMock(side_effect=RuntimeError("boom")))
    assert resp.status == 500
    body = json.loads(resp.body)
    assert body["ok"] is False
    assert "boom" in body["error"]
