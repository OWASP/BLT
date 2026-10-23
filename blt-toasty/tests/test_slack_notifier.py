"""Tests for the Slack triage notifier.

Covers:
    1. Payload carries issue link, CWE, severity, quarantine status, duplicates
    2. Payload never carries the title or report text (redaction invariant)
    3. Quarantine reasons are reduced to a fixed category
    4. Severity tier derived from CWEs
    5. No webhook configured → nothing sent
    6. Slack errors are swallowed
    7. Wiring: duplicate detection, quarantine and redaction notify Slack
"""

from __future__ import annotations

import json
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.slack_notifier import (
    build_payload,
    notify_triage,
    quarantine_category,
    severity_for_cwes,
)

WEBHOOK = "https://hooks.slack.com/services/T000/B000/XXXX"


@pytest.fixture(autouse=True)
def _no_workers_runtime():
    """Run as plain CPython even if another test module leaked a ``js`` mock."""
    with (
        patch.dict(sys.modules, {"js": None, "pyodide": None, "pyodide.ffi": None}),
        patch("src.slack_notifier.fetch", None),
    ):
        yield


PII_TITLE = "SQLi in login, contact alice@example.com 555-123-4567"


def _make_db(*, issue_iid=35, cwe_hints=("CWE-89",), quarantine_reason=None, title=PII_TITLE):
    """Mock D1 handle that answers the notifier's two SELECTs.

    The event row also carries a raw ``title`` so tests can prove the
    notifier never forwards it.
    """

    def prepare_side_effect(sql):
        sql_lower = sql.lower()
        if "from triage_events" in sql_lower:
            row = {"issue_iid": issue_iid, "quarantine_reason": quarantine_reason, "title": title}
        elif "from triage_summaries" in sql_lower:
            row = {"cwe_hints": json.dumps(list(cwe_hints))} if cwe_hints is not None else None
        else:
            row = None
        stmt = MagicMock()
        stmt.bind = MagicMock(return_value=stmt)
        stmt.first = AsyncMock(return_value=row)
        return stmt

    db = MagicMock()
    db.prepare = MagicMock(side_effect=prepare_side_effect)
    return db


class _Env:
    def __init__(self, webhook=WEBHOOK, status=200, fetch_error=None):
        self.SLACK_WEBHOOK_URL = webhook
        self._fetch = AsyncMock()
        if fetch_error:
            self._fetch.side_effect = fetch_error
        else:
            self._fetch.return_value = MagicMock(status=status)


def _sent_payload(env):
    url, options = env._fetch.await_args.args
    assert url == WEBHOOK
    assert options["method"] == "POST"
    return json.loads(options["body"])


# ---------------------------------------------------------------------------
# Payload
# ---------------------------------------------------------------------------


class TestBuildPayload:
    def test_contains_triage_fields(self):
        payload = build_payload(
            "evt-1",
            35,
            ["CWE-89", "CWE-79"],
            quarantined=False,
            duplicates=[{"event_id": "evt-0", "score": 0.912}],
        )
        text = json.dumps(payload)

        assert "https://git.owaspblt.org/BLT/issues/35" in text
        assert "CWE-89 (SQL Injection)" in text
        assert "CWE-79 (Cross-Site Scripting (XSS))" in text
        assert "critical" in text
        assert "*Quarantined*\\nno" in text
        assert "`evt-0` (similarity 0.91)" in text
        assert "evt-1" in text

    def test_no_duplicates_and_unknown_issue(self):
        text = json.dumps(build_payload("evt-1", None, [], quarantined=False))
        assert "unknown issue" in text
        assert "*Possible duplicates*\\nnone" in text
        assert "info" in text

    def test_quarantine_reason_is_categorised_not_forwarded(self):
        reason = "Unexpected error during redaction: ValueError: bob@example.com"
        text = json.dumps(build_payload("evt-1", 35, [], quarantined=True, quarantine_reason=reason))
        assert "yes (redaction error)" in text
        assert "bob@example.com" not in text


class TestHelpers:
    @pytest.mark.parametrize(
        ("cwes", "expected"),
        [
            ([], "info"),
            (["CWE-UNKNOWN"], "info"),
            (["CWE-476"], "low"),
            (["CWE-999"], "medium"),
            (["CWE-79", "CWE-918"], "high"),
            (["CWE-79", "CWE-89"], "critical"),
        ],
    )
    def test_severity_for_cwes(self, cwes, expected):
        assert severity_for_cwes(cwes) == expected

    @pytest.mark.parametrize(
        ("reason", "expected"),
        [
            (None, "unspecified"),
            ("Residual PII after Markdown stripping: 1 entities (EMAIL)", "PII leak (redaction gate)"),
            ("Entity PHONE at [3:15] has confidence 0.40 < threshold 0.85", "PII leak (redaction gate)"),
            ("Unexpected error during redaction: KeyError: x", "redaction error"),
            ("manual review", "other"),
        ],
    )
    def test_quarantine_category(self, reason, expected):
        assert quarantine_category(reason) == expected


# ---------------------------------------------------------------------------
# notify_triage
# ---------------------------------------------------------------------------


class TestNotifyTriage:
    @pytest.mark.asyncio
    async def test_posts_payload_without_title(self):
        env = _Env()
        ok = await notify_triage(env, _make_db(), "evt-1", duplicates=[{"event_id": "evt-0", "score": 0.9}])

        assert ok is True
        payload = _sent_payload(env)
        text = json.dumps(payload)
        assert "CWE-89" in text
        assert "issues/35" in text
        assert "alice@example.com" not in text
        assert "555-123-4567" not in text
        assert "login" not in text

    @pytest.mark.asyncio
    async def test_quarantined_event(self):
        env = _Env()
        db = _make_db(cwe_hints=None, quarantine_reason="Residual PII after Markdown stripping: 1 entities (EMAIL)")
        assert await notify_triage(env, db, "evt-2", quarantined=True) is True
        text = json.dumps(_sent_payload(env))
        assert "Toasty quarantined an issue" in text
        assert "PII leak (redaction gate)" in text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("webhook", [None, "", MagicMock()])
    async def test_skips_without_webhook(self, webhook):
        env = _Env(webhook=webhook)
        assert await notify_triage(env, _make_db(), "evt-1") is False
        env._fetch.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_skips_without_env(self):
        assert await notify_triage(None, _make_db(), "evt-1") is False

    @pytest.mark.asyncio
    async def test_fetch_error_is_swallowed(self):
        env = _Env(fetch_error=RuntimeError("network down"))
        assert await notify_triage(env, _make_db(), "evt-1") is False

    @pytest.mark.asyncio
    async def test_non_2xx_returns_false(self):
        env = _Env(status=404)
        assert await notify_triage(env, _make_db(), "evt-1") is False

    @pytest.mark.asyncio
    async def test_bad_cwe_json_still_notifies(self):
        env = _Env()
        db = _make_db()
        bad_stmt = MagicMock()
        bad_stmt.bind = MagicMock(return_value=bad_stmt)
        bad_stmt.first = AsyncMock(return_value={"cwe_hints": "not json"})
        original = db.prepare.side_effect
        db.prepare.side_effect = lambda sql: bad_stmt if "triage_summaries" in sql else original(sql)

        assert await notify_triage(env, db, "evt-1") is True
        assert "*CWE*\\nnone" in json.dumps(_sent_payload(env))


class TestWorkersRuntime:
    @pytest.mark.asyncio
    async def test_timeout_uses_abort_signal_not_python_timer(self):
        """Under Pyodide the timeout must be AbortSignal.timeout, not a Python setTimeout callback."""
        from src.slack_notifier import SLACK_TIMEOUT_SECONDS, post_to_slack

        timeout_signal = object()
        js = types.ModuleType("js")
        js.AbortSignal = MagicMock()
        js.AbortSignal.timeout = MagicMock(return_value=timeout_signal)
        js.Object = MagicMock()
        js.setTimeout = MagicMock(side_effect=AssertionError("setTimeout must not be used"))
        ffi = types.ModuleType("pyodide.ffi")
        ffi.to_js = MagicMock(side_effect=lambda obj, dict_converter=None: obj)
        pyodide = types.ModuleType("pyodide")
        pyodide.ffi = ffi

        env = _Env()
        with patch.dict(sys.modules, {"js": js, "pyodide": pyodide, "pyodide.ffi": ffi}):
            assert await post_to_slack(WEBHOOK, {"text": "hi"}, env) is True

        js.AbortSignal.timeout.assert_called_once_with(SLACK_TIMEOUT_SECONDS * 1000)
        js.setTimeout.assert_not_called()
        ffi.to_js.assert_called_once()
        options = env._fetch.await_args.args[1]
        assert options["signal"] is timeout_signal


def test_issue_url_is_shared():
    from src.forge_links import issue_url

    assert issue_url(35) == "https://git.owaspblt.org/BLT/issues/35"
    assert issue_url(35) in json.dumps(build_payload("evt-1", 35, [], quarantined=False))


# ---------------------------------------------------------------------------
# Pipeline wiring
# ---------------------------------------------------------------------------


class TestWiring:
    @pytest.mark.asyncio
    async def test_detect_duplicates_notifies_with_confirmed_candidates(self):
        from src.duplicate_detector import detect_duplicates

        db = MagicMock()
        stmt = MagicMock()
        stmt.bind = MagicMock(return_value=stmt)
        stmt.first = AsyncMock(return_value={"status": "redaction_passed"})
        stmt.run = AsyncMock()
        db.prepare = MagicMock(return_value=stmt)
        db.batch = AsyncMock()
        env = MagicMock()
        matches = [{"event_id": "evt-dup", "score": 0.93, "metadata": {}}]

        with (
            patch("src.duplicate_detector.find_duplicates", new=AsyncMock(return_value=matches)),
            patch("src.duplicate_detector.notify_triage", new_callable=AsyncMock) as mock_notify,
        ):
            await detect_duplicates("evt-1", "redacted", "owasp/blt", env, db, MagicMock())

        mock_notify.assert_awaited_once_with(env, db, "evt-1", duplicates=[{"event_id": "evt-dup", "score": 0.93}])

    @pytest.mark.asyncio
    async def test_detect_duplicates_notifies_when_no_matches(self):
        from src.duplicate_detector import detect_duplicates

        db = MagicMock()
        stmt = MagicMock()
        stmt.bind = MagicMock(return_value=stmt)
        stmt.first = AsyncMock(return_value={"status": "redaction_passed"})
        db.prepare = MagicMock(return_value=stmt)
        env = MagicMock()

        with (
            patch("src.duplicate_detector.find_duplicates", new=AsyncMock(return_value=[])),
            patch("src.duplicate_detector.notify_triage", new_callable=AsyncMock) as mock_notify,
        ):
            await detect_duplicates("evt-1", "redacted", "owasp/blt", env, db, MagicMock())

        mock_notify.assert_awaited_once_with(env, db, "evt-1")

    @staticmethod
    def _quarantine_db():
        class Meta:
            changes = 1

        class Result:
            meta = Meta()

        stmt = MagicMock()
        stmt.bind = MagicMock(return_value=stmt)
        stmt.first = AsyncMock(return_value={"id": "evt-1", "status": "pending"})
        db = MagicMock()
        db.prepare = MagicMock(return_value=stmt)
        db.batch = AsyncMock(return_value=[Result(), Result()])
        return db

    @pytest.mark.asyncio
    async def test_quarantine_event_notifies_when_env_given(self):
        from src.state_machine import quarantine_event

        db = self._quarantine_db()
        env = MagicMock()
        with patch("src.slack_notifier.notify_triage", new_callable=AsyncMock) as mock_notify:
            await quarantine_event(db, "evt-1", "reason", env=env, has_vector=False)

        mock_notify.assert_awaited_once_with(env, db, "evt-1", quarantined=True)

    @pytest.mark.asyncio
    async def test_quarantine_event_without_env_does_not_notify(self):
        from src.state_machine import quarantine_event

        with patch("src.slack_notifier.notify_triage", new_callable=AsyncMock) as mock_notify:
            await quarantine_event(self._quarantine_db(), "evt-1", "reason", has_vector=False)

        mock_notify.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_redaction_quarantine_passes_env(self):
        from src.errors import RedactionFailedError
        from src.redaction_engine import redact

        env = MagicMock()
        db = MagicMock()
        with (
            patch("src.redaction_engine.apply_native_redaction", side_effect=ValueError("boom")),
            patch("src.redaction_engine._quarantine_event", new_callable=AsyncMock) as mock_quarantine,
            patch("src.redaction_engine._transition_state", new_callable=AsyncMock),
            pytest.raises(RedactionFailedError),
        ):
            await redact("plain text", env, "evt-1", db)

        assert mock_quarantine.await_args.args[3] is env
