"""Alerts go to a webhook only when a monitor goes down or comes back."""

import asyncio
import json
import types
from unittest.mock import AsyncMock

from test_cron_dispatch import _load_worker

MONITORS = [
    {"id": "site", "name": "Site", "url": "https://site.example/"},
    {"id": "api", "name": "API", "url": "https://api.example/"},
]


def _result(monitor_id, status, previous):
    return {"id": monitor_id, "status": status, "previous_status": previous}


def test_alert_lines_report_changes_only():
    worker = _load_worker()
    lines = worker.Default.alert_lines(MONITORS, [
        _result("site", "failure", "success"),
        _result("api", "failure", "failure"),
    ])
    assert lines == ["- DOWN: Site (https://site.example/)"]

    lines = worker.Default.alert_lines(MONITORS, [
        _result("site", "success", "failure"),
        _result("api", "failure", ""),
    ])
    assert lines == ["- DOWN: API (https://api.example/)",
                     "- Back up: Site (https://site.example/)"]

    assert worker.Default.alert_lines(MONITORS, [_result("site", "success", "success")]) == []


def test_alert_webhook_prefers_forge_channel():
    worker = _load_worker()
    entry = worker.Default(env=types.SimpleNamespace(
        ALERT_WEBHOOK_URL="https://forge.example/api/chat/webhooks/abc",
        SLACK_WEBHOOK_URL="https://hooks.slack.example/x"))
    assert entry.alert_webhook_url() == "https://forge.example/api/chat/webhooks/abc"
    entry = worker.Default(env=types.SimpleNamespace(SLACK_WEBHOOK_URL="https://hooks.slack.example/x"))
    assert entry.alert_webhook_url() == "https://hooks.slack.example/x"
    entry = worker.Default(env=types.SimpleNamespace())
    assert entry.alert_webhook_url() == ""


def test_notify_changes_posts_text_body():
    worker = _load_worker()
    worker.fetch = AsyncMock(return_value=types.SimpleNamespace(ok=True, status=201))
    entry = worker.Default(env=types.SimpleNamespace(ALERT_WEBHOOK_URL="https://forge.example/hook"))
    asyncio.run(entry.notify_changes(MONITORS, [_result("site", "failure", "success")]))
    (url,), kwargs = worker.fetch.call_args
    assert url == "https://forge.example/hook"
    text = json.loads(kwargs["body"])["text"]
    assert "DOWN: Site" in text and "monitor.owaspblt.org" in text

    worker.fetch.reset_mock()
    asyncio.run(entry.notify_changes(MONITORS, [_result("site", "failure", "failure")]))
    worker.fetch.assert_not_called()
