"""Tests for POST /__scheduled, the endpoint the blt-cron dispatcher Worker calls.

src/index.py only runs inside the Cloudflare Python runtime, so the ``js`` and
``pyodide`` modules and the sibling handler modules are stubbed here.  Run with:

    python3 -m unittest discover -s tests
"""

import asyncio
import importlib.util
import json
import pathlib
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch
from urllib.parse import urlparse

SRC = pathlib.Path(__file__).resolve().parent.parent / "src"


class _Response:
    def __init__(self, body="", init=None):
        init = init or {}
        self.body = body
        self.status = init.get("status", 200)
        self.headers = init.get("headers", {})

    @classmethod
    def new(cls, body="", init=None):
        return cls(body, init)


class _URL:
    def __init__(self, url):
        self.pathname = urlparse(url).path

    @classmethod
    def new(cls, url):
        return cls(url)


def _load_index():
    stubs = {
        "js": types.SimpleNamespace(
            Response=_Response, URL=_URL, Request=object,
            Object=types.SimpleNamespace(fromEntries=dict),
        ),
        "pyodide": types.ModuleType("pyodide"),
        "pyodide.ffi": types.SimpleNamespace(to_js=lambda value, **_kw: value),
    }
    # Sibling modules pull in the runtime too; index.py only needs their names.
    stubs["slack_notifier"] = types.SimpleNamespace(
        notify_slack_exception=AsyncMock(), notify_slack_error=AsyncMock())
    stubs["templates"] = types.SimpleNamespace(get_404_html=lambda: "")
    handler_names = [
        "handle_add_pr", "handle_list_prs", "handle_list_repos", "handle_list_authors",
        "handle_refresh_pr", "handle_batch_refresh_prs", "handle_refresh_org",
        "handle_rate_limit", "handle_status", "handle_pr_updates_check", "handle_get_pr",
        "handle_github_webhook", "handle_pr_timeline", "handle_pr_review_analysis",
        "handle_pr_readiness", "handle_scheduled_refresh",
    ]
    stubs["handlers"] = types.SimpleNamespace(**{n: AsyncMock() for n in handler_names})
    stubs["auth_handlers"] = types.SimpleNamespace(**{n: AsyncMock() for n in (
        "handle_auth_login", "handle_auth_callback", "handle_auth_user", "handle_auth_logout")})
    with patch.dict(sys.modules, stubs):
        spec = importlib.util.spec_from_file_location("leaf_index", SRC / "index.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


index = _load_index()


class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key, default)


def _request(method="POST", secret=None, body=None):
    headers = _Headers({"X-BLT-Cron-Secret": secret} if secret is not None else {})
    return types.SimpleNamespace(
        method=method,
        url="https://cron.internal/__scheduled",
        headers=headers,
        text=AsyncMock(return_value=json.dumps(body if body is not None else {})),
    )


class CronDispatchTests(unittest.TestCase):
    def _fetch(self, req, env, handler=None):
        handler = handler or AsyncMock()

        async def run():
            with patch.object(index, "on_scheduled", new=handler):
                return await index.on_fetch(req, env)

        return asyncio.run(run()), handler

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
        req = _request(secret="s3cret", body={"cron": "0 * * * *", "scheduledTime": 1760000000000})
        resp, handler = self._fetch(req, env)
        self.assertEqual(resp.status, 200)
        self.assertEqual(json.loads(resp.body), {"ok": True})
        handler.assert_awaited_once()
        event, called_env, _ctx = handler.await_args.args
        self.assertIs(called_env, env)
        self.assertEqual(event.cron, "0 * * * *")
        self.assertEqual(event.scheduledTime, 1760000000000)
        self.assertEqual(event.type, "scheduled")

    def test_handler_exception_returns_500(self):
        env = types.SimpleNamespace(CRON_SECRET="s3cret")
        req = _request(secret="s3cret", body={"cron": "0 * * * *", "scheduledTime": 1})
        resp, _ = self._fetch(req, env, handler=AsyncMock(side_effect=RuntimeError("boom")))
        self.assertEqual(resp.status, 500)
        body = json.loads(resp.body)
        self.assertFalse(body["ok"])
        self.assertIn("boom", body["error"])


if __name__ == "__main__":
    unittest.main()
