"""Tests for POST /__scheduled, the endpoint the blt-cron dispatcher Worker calls.

workers/main.py imports the Cloudflare ``js`` and ``pyodide`` runtime modules,
which are stubbed here.
"""
import asyncio
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
WORKERS = ROOT / "workers"


class _Response:
    def __init__(self, body, init):
        self.body = body
        self.status = (init or {}).get("status", 200)

    @classmethod
    def new(cls, body=None, init=None):
        return cls(body, init)


def _load_main():
    js = types.ModuleType("js")
    for name in ("Request", "Headers", "crypto", "TextEncoder", "TextDecoder", "URL", "fetch", "Date"):
        setattr(js, name, MagicMock())
    js.Response = _Response
    js.Object = types.SimpleNamespace(fromEntries=dict)
    ffi = types.ModuleType("pyodide.ffi")
    ffi.to_js = lambda value, **_kw: value
    pyodide = types.ModuleType("pyodide")
    pyodide.ffi = ffi
    stubs = {"js": js, "pyodide": pyodide, "pyodide.ffi": ffi}
    with patch.dict(sys.modules, stubs), patch.object(sys, "path", [str(WORKERS)] + sys.path):
        spec = importlib.util.spec_from_file_location("sizzle_main", WORKERS / "main.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


main = _load_main()


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


class TestCronDispatch(unittest.TestCase):
    def _fetch(self, req, env, handler=None):
        handler = handler or AsyncMock()
        with patch.object(main, "on_scheduled", new=handler), \
                patch.object(main, "handle_request", new=AsyncMock()) as routed:
            resp = asyncio.run(main.on_fetch(req, env))
        routed.assert_not_called()
        return resp, handler

    def test_missing_secret_returns_403(self):
        resp, handler = self._fetch(_request(), types.SimpleNamespace(CRON_SECRET="s3cret"))
        self.assertEqual(resp.status, 403)
        handler.assert_not_called()

    def test_wrong_secret_returns_403(self):
        resp, handler = self._fetch(_request(secret="nope"), types.SimpleNamespace(CRON_SECRET="s3cret"))
        self.assertEqual(resp.status, 403)
        handler.assert_not_called()

    def test_unset_cron_secret_refuses(self):
        resp, handler = self._fetch(_request(secret=""), types.SimpleNamespace())
        self.assertEqual(resp.status, 403)
        handler.assert_not_called()

    def test_get_returns_405(self):
        resp, handler = self._fetch(_request(method="GET", secret="s3cret"),
                                    types.SimpleNamespace(CRON_SECRET="s3cret"))
        self.assertEqual(resp.status, 405)
        handler.assert_not_called()

    def test_valid_request_runs_scheduled_handler(self):
        env = types.SimpleNamespace(CRON_SECRET="s3cret")
        req = _request(secret="s3cret", body={"cron": "0 * * * *", "scheduledTime": 1760000400000})
        resp, handler = self._fetch(req, env)
        self.assertEqual(resp.status, 200)
        self.assertEqual(json.loads(resp.body), {"ok": True})
        handler.assert_awaited_once()
        event, called_env = handler.await_args.args
        self.assertIs(called_env, env)
        self.assertEqual(event.cron, "0 * * * *")
        self.assertEqual(event.scheduledTime, 1760000400000)
        self.assertEqual(event.type, "scheduled")

    def test_handler_exception_returns_500(self):
        env = types.SimpleNamespace(CRON_SECRET="s3cret")
        req = _request(secret="s3cret", body={"cron": "0 * * * *", "scheduledTime": 1})
        resp, _ = self._fetch(req, env, handler=AsyncMock(side_effect=RuntimeError("boom")))
        self.assertEqual(resp.status, 500)
        body = json.loads(resp.body)
        self.assertFalse(body["ok"])
        self.assertIn("boom", body["error"])

    def test_wrangler_routes_dispatch_to_worker_without_cron_trigger(self):
        config = (ROOT / "wrangler.toml").read_text()
        self.assertIn('"/__scheduled"', config)
        self.assertIn("crons = []", config)


if __name__ == "__main__":
    unittest.main(verbosity=2)
