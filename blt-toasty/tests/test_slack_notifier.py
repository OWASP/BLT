"""Tests for the Slack triage notifier.

Covers:
    1. Payload carries issue link, CWE, severity, quarantine status, duplicates
    2. Severity is labelled as a CWE estimate; unknown CWEs are "unrated,
       needs review"; a valid assessed severity replaces the estimate
    3. Trust boundary: crafted values in every interpolated field cannot form
       Slack links, mentions or formatting
    4. Report text and PII stored in D1 never reach Slack
    5. No webhook configured → nothing sent; Slack errors are swallowed
    6. Wiring: duplicate detection, quarantine and redaction notify Slack

D1 is the SQLite-backed ``sqlite_d1`` fixture from ``conftest.py``: the real
migrations are applied and the notifier's queries run for real.
"""

from __future__ import annotations

import json
import re
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.slack_notifier import (
    ESTIMATE_NOTE,
    INVALID_ID,
    build_payload,
    escape_mrkdwn,
    notify_triage,
    quarantine_category,
    safe_cwe_ids,
    safe_event_id,
    safe_issue_iid,
    safe_score,
    severity_for_cwes,
)

WEBHOOK = "https://hooks.slack.com/services/T000/B000/XXXX"
EVENT_ID = "0123456789abcdef0123456789abcdef"  # secrets.token_hex(16)
DUP_ID = "fedcba9876543210fedcba9876543210"
PII = ("alice@example.com", "555-123-4567")

# Slack control sequences a crafted value could try to smuggle in.
CRAFTED = [
    "<https://evil.example|Click to verify>",
    "<!channel>",
    "<@U123ABC>",
    "x` <https://evil.example|y> `",
    "*bold* _it_ ~strike~",
    "35|evil>",
    "a" * 500,
    "line1\nline2",
    "&lt;script&gt;",
]


@pytest.fixture(autouse=True)
def _no_workers_runtime():
    """Run as plain CPython even if another test module leaked a ``js`` mock."""
    with (
        patch.dict(sys.modules, {"js": None, "pyodide": None, "pyodide.ffi": None}),
        patch("src.slack_notifier.fetch", None),
    ):
        yield


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


def _mrkdwn_texts(payload):
    """Every string Slack will render as mrkdwn, including the fallback text."""
    texts = [payload["text"]]
    for block in payload["blocks"]:
        if block["type"] == "section":
            texts += [f["text"] for f in block.get("fields", [])]
            if "text" in block:
                texts.append(block["text"]["text"])
        elif block["type"] == "context":
            texts += [e["text"] for e in block["elements"]]
    return texts


def _assert_no_injected_markup(payload):
    """Only the notifier's own issue link may use Slack's <...> syntax."""
    for text in _mrkdwn_texts(payload):
        for match in re.findall(r"<[^>]*>", text):
            assert re.fullmatch(r"<https://git\.owaspblt\.org/BLT/issues/\d+\|#\d+>", match), match
        assert "<!" not in text and "<@" not in text


# ---------------------------------------------------------------------------
# Payload
# ---------------------------------------------------------------------------


class TestBuildPayload:
    def test_contains_triage_fields(self):
        payload = build_payload(
            EVENT_ID, 35, ["CWE-89", "CWE-79"], quarantined=False, duplicates=[{"event_id": DUP_ID, "score": 0.912}]
        )
        text = json.dumps(payload)

        assert "<https://git.owaspblt.org/BLT/issues/35|#35>" in text
        assert "CWE-89 (SQL Injection)" in text
        assert "CWE-79 (Cross-Site Scripting (XSS))" in text
        assert "*Quarantined*\\nno" in text
        assert f"`{DUP_ID}` (similarity 0.91)" in text
        assert f"Triage ID `{EVENT_ID}`" in text

    def test_no_duplicates_and_unknown_issue(self):
        text = json.dumps(build_payload(EVENT_ID, None, [], quarantined=False))
        assert "unknown issue" in text
        assert "*Possible duplicates*\\nnone" in text

    def test_quarantine_reason_is_categorised_not_forwarded(self):
        reason = "Unexpected error during redaction: ValueError: bob@example.com"
        text = json.dumps(build_payload(EVENT_ID, 35, [], quarantined=True, quarantine_reason=reason))
        assert "yes (redaction error)" in text
        assert "bob@example.com" not in text


class TestSeverity:
    @pytest.mark.parametrize(
        ("cwes", "expected"),
        [
            ([], "unrated"),
            (["CWE-UNKNOWN"], "unrated"),
            (["CWE-999"], "unrated"),
            (["CWE-476"], "low"),
            (["CWE-999", "CWE-79"], "medium"),
            (["CWE-79", "CWE-918"], "high"),
            (["CWE-79", "CWE-89"], "critical"),
        ],
    )
    def test_severity_for_cwes(self, cwes, expected):
        assert severity_for_cwes(cwes) == expected

    def test_estimate_is_labelled_as_estimate(self):
        payload = build_payload(EVENT_ID, 35, ["CWE-89"], quarantined=False)
        text = json.dumps(payload)
        assert "*Est. severity (from CWE type)*\\n:red_circle: critical" in text
        assert "(est. severity critical)" in payload["text"]
        assert ESTIMATE_NOTE in text

    @pytest.mark.parametrize("cwes", [[], ["CWE-UNKNOWN"], ["CWE-12345"]])
    def test_unknown_cwe_is_unrated_needs_review(self, cwes):
        payload = build_payload(EVENT_ID, 35, cwes, quarantined=False)
        text = json.dumps(payload)
        assert ":grey_question: unrated, needs review" in text
        assert "(unrated, needs review)" in payload["text"]
        for tier in ("critical", "high", "medium", "low", "info"):
            assert f"est. severity {tier}" not in text

    def test_assessed_severity_replaces_estimate(self):
        payload = build_payload(EVENT_ID, 35, ["CWE-89"], quarantined=False, assessed_severity="Low")
        text = json.dumps(payload)
        assert "*Severity (assessed)*\\n:large_blue_circle: low" in text
        assert "(severity low)" in payload["text"]
        assert "Est. severity" not in text
        assert ESTIMATE_NOTE not in text

    @pytest.mark.parametrize("assessed", ["urgent", "<!channel>", "", 5, None])
    def test_invalid_assessed_severity_falls_back_to_estimate(self, assessed):
        text = json.dumps(build_payload(EVENT_ID, 35, ["CWE-89"], quarantined=False, assessed_severity=assessed))
        assert "*Est. severity (from CWE type)*" in text
        assert ESTIMATE_NOTE in text


class TestQuarantineCategory:
    @pytest.mark.parametrize(
        ("reason", "expected"),
        [
            (None, "unspecified"),
            ("Residual PII after Markdown stripping: 1 entities (EMAIL)", "PII leak (redaction gate)"),
            ("Entity PHONE at [3:15] has confidence 0.40 < threshold 0.85", "PII leak (redaction gate)"),
            ("Unexpected error during redaction: KeyError: x", "redaction error"),
            ("<https://evil.example|x>", "other"),
        ],
    )
    def test_quarantine_category(self, reason, expected):
        assert quarantine_category(reason) == expected


# ---------------------------------------------------------------------------
# Trust boundary: every interpolated value
# ---------------------------------------------------------------------------


class TestValidators:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [(35, 35), ("35", 35), (0, None), (-1, None), (True, None), (10**12, None), ("35a", None), ("٣٥", None)]
        + [(c, None) for c in CRAFTED],
    )
    def test_safe_issue_iid(self, value, expected):
        assert safe_issue_iid(value) == expected

    @pytest.mark.parametrize(
        ("value", "ok"),
        [(EVENT_ID, True), ("shadow:" + EVENT_ID, True), ("evt-1", True), ("", False), (None, False), (35, False)]
        + [(c, False) for c in CRAFTED],
    )
    def test_safe_event_id(self, value, ok):
        assert safe_event_id(value) == (value if ok else None)

    def test_safe_cwe_ids_keeps_only_well_formed(self):
        values = ["CWE-89", "CWE-89", "CWE-UNKNOWN", "cwe-79", "CWE-79 ", "CWE-123456", 89, None, *CRAFTED]
        assert safe_cwe_ids(values) == ["CWE-89", "CWE-UNKNOWN"]
        assert safe_cwe_ids("CWE-89") == []
        assert len(safe_cwe_ids([f"CWE-{i}" for i in range(50)])) == 10

    @pytest.mark.parametrize(
        ("value", "expected"),
        [(0.9, 0.9), (1, 1.0), (0, 0.0), (1.01, None), (-0.1, None), (float("nan"), None), (float("inf"), None)]
        + [(True, None), ("0.9", None), (None, None)],
    )
    def test_safe_score(self, value, expected):
        assert safe_score(value) == expected

    def test_escape_mrkdwn(self):
        assert escape_mrkdwn("<a href> & <!channel>") == "&lt;a href&gt; &amp; &lt;!channel&gt;"


class TestCraftedInput:
    @pytest.mark.parametrize("crafted", CRAFTED)
    def test_crafted_event_id(self, crafted):
        payload = build_payload(crafted, 35, ["CWE-89"], quarantined=False)
        _assert_no_injected_markup(payload)
        assert f"Triage ID {INVALID_ID}" in json.dumps(payload)

    @pytest.mark.parametrize("crafted", CRAFTED)
    def test_crafted_issue_number(self, crafted):
        payload = build_payload(EVENT_ID, crafted, ["CWE-89"], quarantined=False)
        _assert_no_injected_markup(payload)
        assert "unknown issue" in payload["text"]

    @pytest.mark.parametrize("crafted", CRAFTED)
    def test_crafted_duplicate(self, crafted):
        payload = build_payload(
            EVENT_ID, 35, ["CWE-89"], quarantined=False, duplicates=[{"event_id": crafted, "score": crafted}]
        )
        _assert_no_injected_markup(payload)
        assert payload["blocks"][2]["text"]["text"] == f"*Possible duplicates*\n• {INVALID_ID} (similarity n/a)"

    @pytest.mark.parametrize("crafted", CRAFTED)
    def test_crafted_cwe(self, crafted):
        payload = build_payload(EVENT_ID, 35, [crafted, "CWE-79"], quarantined=False)
        _assert_no_injected_markup(payload)
        assert "*CWE*\\nCWE-79 (Cross-Site Scripting (XSS))" in json.dumps(payload)

    @pytest.mark.parametrize("bad", [None, "x", 5, [None, "x", 5], [{"event_id": DUP_ID}]])
    def test_malformed_duplicates_do_not_raise(self, bad):
        build_payload(EVENT_ID, 35, [], quarantined=False, duplicates=bad)

    def test_cwe_labels_are_escaped(self):
        with patch.dict("src.slack_notifier.CWE_LABELS", {"CWE-89": "<https://evil.example|SQLi>"}):
            payload = build_payload(EVENT_ID, 35, ["CWE-89"], quarantined=False)
        _assert_no_injected_markup(payload)
        assert "&lt;https://evil.example|SQLi&gt;" in json.dumps(payload)


# ---------------------------------------------------------------------------
# notify_triage against SQLite-backed D1
# ---------------------------------------------------------------------------


class TestNotifyTriage:
    @pytest.mark.asyncio
    async def test_posts_metadata_only(self, sqlite_d1):
        sqlite_d1.add_event(EVENT_ID, issue_iid=35)
        sqlite_d1.add_summary(
            EVENT_ID,
            cwe_hints='["CWE-89"]',
            executive_summary=f"SQLi in /login reported by {PII[0]}",
            reviewer_pack=f"call {PII[1]}",
        )
        env = _Env()

        ok = await notify_triage(env, sqlite_d1, EVENT_ID, duplicates=[{"event_id": DUP_ID, "score": 0.9}])

        assert ok is True
        text = json.dumps(_sent_payload(env))
        assert "CWE-89" in text and "issues/35" in text and DUP_ID in text
        for leaked in (*PII, "/login", "SQLi in"):
            assert leaked not in text

    @pytest.mark.asyncio
    async def test_reads_only(self, sqlite_d1):
        sqlite_d1.add_event(EVENT_ID)
        await notify_triage(_Env(), sqlite_d1, EVENT_ID)
        assert sqlite_d1.statements and all(s.lstrip().upper().startswith("SELECT") for s in sqlite_d1.statements)

    @pytest.mark.asyncio
    async def test_quarantined_event(self, sqlite_d1):
        sqlite_d1.add_event(
            EVENT_ID, status="quarantined", quarantine_reason="Residual PII after Markdown stripping: 1 entities"
        )
        env = _Env()
        assert await notify_triage(env, sqlite_d1, EVENT_ID, quarantined=True) is True
        payload = _sent_payload(env)
        text = json.dumps(payload)
        assert "Toasty quarantined an issue" in text
        assert "PII leak (redaction gate)" in text
        assert "unrated, needs review" in text  # no summary row, so no CWE

    @pytest.mark.asyncio
    async def test_crafted_values_stored_in_d1(self, sqlite_d1):
        crafted = "<https://evil.example|Click to verify>"
        sqlite_d1.add_event(EVENT_ID, issue_iid=crafted)  # SQLite stores text in an INTEGER column
        sqlite_d1.add_summary(EVENT_ID, cwe_hints=json.dumps([crafted, "CWE-79"]))
        env = _Env()
        assert await notify_triage(env, sqlite_d1, EVENT_ID) is True
        payload = _sent_payload(env)
        _assert_no_injected_markup(payload)
        assert "unknown issue" in payload["text"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("cwe_hints", ["not json", '{"a": 1}', "null", '"CWE-89"'])
    async def test_malformed_cwe_hints_still_notifies(self, sqlite_d1, cwe_hints):
        sqlite_d1.add_event(EVENT_ID)
        sqlite_d1.add_summary(EVENT_ID, cwe_hints=cwe_hints)
        env = _Env()
        assert await notify_triage(env, sqlite_d1, EVENT_ID) is True
        assert "*CWE*\\nnone" in json.dumps(_sent_payload(env))

    @pytest.mark.asyncio
    async def test_missing_event_row_still_notifies(self, sqlite_d1):
        env = _Env()
        assert await notify_triage(env, sqlite_d1, EVENT_ID) is True
        assert "unknown issue" in _sent_payload(env)["text"]

    @pytest.mark.asyncio
    async def test_assessed_severity_is_passed_through(self, sqlite_d1):
        sqlite_d1.add_event(EVENT_ID)
        sqlite_d1.add_summary(EVENT_ID, cwe_hints='["CWE-89"]')
        env = _Env()
        await notify_triage(env, sqlite_d1, EVENT_ID, assessed_severity="medium")
        assert "*Severity (assessed)*" in json.dumps(_sent_payload(env))

    @pytest.mark.asyncio
    @pytest.mark.parametrize("webhook", [None, "", MagicMock()])
    async def test_skips_without_webhook(self, sqlite_d1, webhook):
        env = _Env(webhook=webhook)
        assert await notify_triage(env, sqlite_d1, EVENT_ID) is False
        env._fetch.assert_not_awaited()
        assert sqlite_d1.statements == []

    @pytest.mark.asyncio
    async def test_skips_without_env(self, sqlite_d1):
        assert await notify_triage(None, sqlite_d1, EVENT_ID) is False

    @pytest.mark.asyncio
    async def test_fetch_error_is_swallowed(self, sqlite_d1):
        env = _Env(fetch_error=RuntimeError("network down"))
        assert await notify_triage(env, sqlite_d1, EVENT_ID) is False

    @pytest.mark.asyncio
    async def test_non_2xx_returns_false(self, sqlite_d1):
        assert await notify_triage(_Env(status=404), sqlite_d1, EVENT_ID) is False


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
