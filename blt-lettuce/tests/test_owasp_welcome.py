"""Tests for the OWASP welcome bot (src/lettuce/welcome_bot.py) and its /webhook wiring.

D1 is stood in for by SQLite with the real migrations applied, so the SQL is exercised.
Slack is a fake recorded per test.
"""

import asyncio
import base64
import hashlib
import hmac
import importlib.util
import json
import pathlib
import sqlite3
import sys
import time
import types
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lettuce import welcome_bot as wb  # noqa: E402

OWASP = "T04T40NHX"
BLT = "T070JPE5BQQ"
SECRET = "test-signing-secret"


# --------------------------------------------------------------------------- fakes


class D1Result(dict):
    """A D1 result: worker.py reads .results / .meta, welcome_bot reads it as a dict."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as error:
            raise AttributeError(name) from error


class FakeStatement:
    def __init__(self, db, sql):
        self.db, self.sql, self.params = db, sql, []

    def bind(self, *params):
        self.params = list(params)
        return self

    async def all(self):
        cur = self.db.conn.execute(self.sql, self.params)
        cols = [c[0] for c in cur.description or []]
        return D1Result(results=[dict(zip(cols, row)) for row in cur.fetchall()], meta={})

    async def first(self):
        rows = (await self.all())["results"]
        return rows[0] if rows else None

    async def run(self):
        cur = self.db.conn.execute(self.sql, self.params)
        self.db.conn.commit()
        return D1Result(results=[], meta={"changes": cur.rowcount})


class FakeD1:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        for name in ("001_initial.sql", "007_owasp_welcome.sql"):
            self.conn.executescript((ROOT / "migrations" / name).read_text())

    def prepare(self, sql):
        return FakeStatement(self, sql)

    def rows(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def add_workspace(self, team_id=OWASP, token="xoxb-owasp"):
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO workspaces (team_id, team_name, access_token, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            [team_id, team_id, token, now, now],
        )
        self.conn.commit()


class FakeSlack:
    """Records calls; answers from per-method queues (default: success)."""

    def __init__(self):
        self.calls = []
        self.queued = {}

    def queue(self, method, *responses):
        self.queued.setdefault(method, []).extend(responses)

    async def __call__(self, url, method, headers, body):
        api = url.split("/api/", 1)[1].split("?", 1)[0]
        self.calls.append({"api": api, "headers": headers, "body": json.loads(body) if body else None,
                           "url": url})
        if self.queued.get(api):
            status, payload = self.queued[api].pop(0)
            return status, json.dumps(payload), ""
        defaults = {
            "conversations.open": {"ok": True, "channel": {"id": "D123"}},
            "chat.postMessage": {"ok": True, "ts": "1700000000.000100", "channel": "D123"},
            "auth.test": {"ok": True, "team_id": OWASP, "user_id": "UBOT"},
            "conversations.list": {"ok": True, "channels": [], "response_metadata": {}},
        }
        return 200, json.dumps(defaults.get(api, {"ok": True})), ""

    def apis(self):
        return [c["api"] for c in self.calls]


@pytest.fixture
def db():
    d1 = FakeD1()
    d1.add_workspace()
    return d1


@pytest.fixture
def slack(monkeypatch):
    fake = FakeSlack()
    monkeypatch.setattr(wb, "_http_request", fake)
    monkeypatch.setattr(wb, "_sleep", AsyncMock())
    wb._public_stats_cache.clear()
    return fake


def make_env(db, **values):
    base = {"DB": db, "BASE_URL": "https://lettuce.owaspblt.org", "SIGNING_SECRET": SECRET}
    base.update(values)
    return types.SimpleNamespace(**base)


def team_join_body(event_id="Ev1", user_id="U1", team_id=OWASP, **user_fields):
    user = {"id": user_id, "team_id": team_id, "name": "newbie"}
    user.update(user_fields)
    return {
        "type": "event_callback",
        "team_id": team_id,
        "event_id": event_id,
        "event_time": 1700000000,
        "event": {"type": "team_join", "user": user},
    }


class Ctx:
    """ExecutionContext stand-in: keeps waitUntil work to run after the 'response'."""

    def __init__(self):
        self.pending = []

    def waitUntil(self, awaitable):
        self.pending.append(awaitable)

    async def drain(self):
        while self.pending:
            await self.pending.pop(0)


def run(coro):
    return asyncio.run(coro)


# --------------------------------------------------------------------------- worker loading


class _Headers:
    def __init__(self, data=None):
        self._data = dict(data or {})

    @classmethod
    def new(cls, data=None):
        return cls(data)

    def set(self, key, value):
        self._data[key] = value

    def append(self, key, value):
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

    @classmethod
    def json(cls, data, init=None):
        return cls(json.dumps(data), init or {})


def _load_worker():
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
        spec = importlib.util.spec_from_file_location("lettuce_worker_welcome", SRC / "worker.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


worker = _load_worker()


def signed_request(body, secret=SECRET, path="/webhook", ts=None, extra_headers=None):
    text = json.dumps(body)
    ts = str(ts if ts is not None else int(time.time()))
    sig = "v0=" + hmac.new(secret.encode(), "v0:{0}:{1}".format(ts, text).encode(), hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-Slack-Request-Timestamp": ts,
        "X-Slack-Signature": sig,
    }
    headers.update(extra_headers or {})
    return types.SimpleNamespace(
        method="POST", url="https://lettuce.owaspblt.org" + path,
        headers=_Headers(headers), text=AsyncMock(return_value=text),
    )


def get_request(path, headers=None):
    return types.SimpleNamespace(
        method="GET", url="https://lettuce.owaspblt.org" + path,
        headers=_Headers(headers or {}), text=AsyncMock(return_value=""),
    )


# --------------------------------------------------------------------------- signature


def test_unsigned_team_join_is_rejected_before_anything_is_recorded(db, slack):
    env = make_env(db, WELCOME_ENABLED="true")
    req = signed_request(team_join_body(), secret="wrong-secret")
    resp = run(worker.handle_request(req, env, Ctx()))
    assert resp.status == 401
    assert db.rows("SELECT * FROM team_joins") == []
    assert slack.calls == []


def test_stale_signature_is_rejected(db, slack):
    env = make_env(db, WELCOME_ENABLED="true")
    req = signed_request(team_join_body(), ts=int(time.time()) - 600)
    resp = run(worker.handle_request(req, env, Ctx()))
    assert resp.status == 401
    assert db.rows("SELECT * FROM team_joins") == []


# --------------------------------------------------------------------------- ack then send


def test_webhook_acks_before_sending_then_welcomes(db, slack, monkeypatch):
    env = make_env(db, WELCOME_ENABLED="true")
    ctx = Ctx()

    async def scenario():
        gate = asyncio.Event()

        async def slow_slack(url, method, headers, body):
            await gate.wait()  # Slack hasn't answered yet
            return await slack(url, method, headers, body)

        monkeypatch.setattr(wb, "_http_request", slow_slack)
        resp = await worker.handle_request(signed_request(team_join_body()), env, ctx)
        # The response exists while the DM is still waiting on Slack.
        assert resp.status == 200
        assert json.loads(resp.body)["action"] == "accepted"
        assert len(ctx.pending) == 1 and not ctx.pending[0].done()
        row = db.rows("SELECT * FROM team_joins")[0]
        assert row["welcome_status"] == "pending" and row["tracking_id"]
        gate.set()
        await ctx.drain()

    run(scenario())
    assert slack.apis() == ["conversations.open", "chat.postMessage"]
    row = db.rows("SELECT * FROM team_joins")[0]
    assert row["welcome_status"] == "sent"
    assert row["delivered_at"] and row["sent_at"] and row["message_ts"] == "1700000000.000100"
    assert row["dm_channel"] == "D123" and row["attempts"] == 2
    assert slack.calls[0]["headers"]["Authorization"] == "Bearer xoxb-owasp"


def test_team_join_skips_webhook_received_debug_row(db, slack):
    env = make_env(db, WELCOME_ENABLED="true")
    run(worker.handle_request(signed_request(team_join_body()), env, Ctx()))
    assert db.rows("SELECT * FROM events") == []


# --------------------------------------------------------------------------- dedupe


def test_slack_retry_of_same_event_is_welcomed_once(db, slack):
    env = make_env(db, WELCOME_ENABLED="true")
    ctx = Ctx()
    first = run(worker.handle_request(signed_request(team_join_body()), env, ctx))
    retry = run(worker.handle_request(
        signed_request(team_join_body(), extra_headers={"X-Slack-Retry-Num": "1"}), env, ctx))
    assert json.loads(first.body)["action"] == "accepted"
    assert json.loads(retry.body)["action"] == "duplicate"
    run(ctx.drain())
    assert slack.apis().count("chat.postMessage") == 1
    assert len(db.rows("SELECT * FROM team_joins")) == 1


def test_user_welcomed_recently_is_not_welcomed_again(db, slack):
    env = make_env(db, WELCOME_ENABLED="true")
    run(wb.accept_team_join(env, None, team_join_body("Ev1"), OWASP))
    run(wb.accept_team_join(env, None, team_join_body("Ev2"), OWASP))
    assert slack.apis().count("chat.postMessage") == 1
    statuses = [r["welcome_status"] for r in db.rows("SELECT * FROM team_joins ORDER BY id")]
    assert statuses == ["sent", "skipped"]


def test_bots_and_deleted_users_are_recorded_not_welcomed(db, slack):
    env = make_env(db, WELCOME_ENABLED="true")
    run(wb.accept_team_join(env, None, team_join_body("Ev1", "UB", is_bot=True), OWASP))
    run(wb.accept_team_join(env, None, team_join_body("Ev2", "UD", deleted=True), OWASP))
    assert slack.calls == []
    rows = db.rows("SELECT welcome_status, detail FROM team_joins ORDER BY id")
    assert rows == [{"welcome_status": "skipped", "detail": "bot_user"},
                    {"welcome_status": "skipped", "detail": "deleted_user"}]


def test_record_failure_still_welcomes_first_delivery_but_not_a_retry(slack):
    broken = types.SimpleNamespace(prepare=Mock(side_effect=RuntimeError("no such table")))
    env = types.SimpleNamespace(DB=broken, WELCOME_ENABLED="true", WELCOME_SLACK_TOKEN="xoxb-env")
    out = run(wb.accept_team_join(env, None, team_join_body(), OWASP))
    assert out["action"] == "accepted"
    assert slack.apis() == ["conversations.open", "chat.postMessage"]
    slack.calls.clear()
    out = run(wb.accept_team_join(env, None, team_join_body(), OWASP, retry_num="1"))
    assert out["action"] == "duplicate" and slack.calls == []


# --------------------------------------------------------------------------- kill switch


@pytest.mark.parametrize("value", [None, "", "false", "0", "off", "no"])
def test_welcome_disabled_records_join_without_dm(db, slack, value):
    env = make_env(db) if value is None else make_env(db, WELCOME_ENABLED=value)
    ctx = Ctx()
    resp = run(worker.handle_request(signed_request(team_join_body()), env, ctx))
    run(ctx.drain())
    assert json.loads(resp.body)["welcome"] == "disabled"
    assert slack.calls == []
    assert db.rows("SELECT welcome_status FROM team_joins") == [{"welcome_status": "disabled"}]


def test_non_welcome_workspace_keeps_legacy_path(db, slack):
    env = make_env(db, WELCOME_ENABLED="true")
    with patch.object(worker, "handle_team_join", new=AsyncMock(return_value={"ok": True})) as legacy:
        resp = run(worker.handle_request(signed_request(team_join_body(team_id=BLT)), env, Ctx()))
    assert resp.status == 200
    legacy.assert_awaited_once()
    assert db.rows("SELECT * FROM team_joins") == []


# --------------------------------------------------------------------------- retry


def test_transient_slack_error_is_retried_once(db, slack):
    env = make_env(db, WELCOME_ENABLED="true")
    slack.queue("chat.postMessage", (429, {"ok": False, "error": "ratelimited"}))
    run(wb.accept_team_join(env, None, team_join_body(), OWASP))
    assert slack.apis() == ["conversations.open", "chat.postMessage", "chat.postMessage"]
    row = db.rows("SELECT welcome_status, attempts FROM team_joins")[0]
    assert row == {"welcome_status": "sent", "attempts": 3}


def test_second_transient_failure_is_recorded_not_retried_forever(db, slack):
    env = make_env(db, WELCOME_ENABLED="true")
    slack.queue("conversations.open", (503, {}), (503, {}))
    run(wb.accept_team_join(env, None, team_join_body(), OWASP))
    assert slack.apis() == ["conversations.open", "conversations.open"]
    row = db.rows("SELECT welcome_status, detail FROM team_joins")[0]
    assert row == {"welcome_status": "failed", "detail": "conversations.open:http_503"}


def test_permanent_slack_error_is_not_retried(db, slack, capsys):
    env = make_env(db, WELCOME_ENABLED="true")
    slack.queue("conversations.open", (200, {"ok": False, "error": "user_not_found"}))
    run(wb.accept_team_join(env, None, team_join_body(), OWASP))
    assert slack.apis() == ["conversations.open"]
    out = capsys.readouterr().out
    assert "user_not_found" in out and "xoxb-owasp" not in out


def test_network_exception_is_retried(db, slack):
    calls = {"n": 0}

    async def flaky(url, method, headers, body):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("reset")
        return await slack(url, method, headers, body)

    wb._http_request = flaky
    try:
        result = run(wb.slack_call("xoxb-x", "auth.test", {}))
    finally:
        wb._http_request = slack
    assert result["ok"] and result["attempts"] == 2


def test_missing_token_fails_honestly(slack):
    d1 = FakeD1()  # no workspace row, no secret
    env = make_env(d1, WELCOME_ENABLED="true")
    run(wb.accept_team_join(env, None, team_join_body(), OWASP))
    assert slack.calls == []
    assert d1.rows("SELECT welcome_status, detail FROM team_joins")[0] == {
        "welcome_status": "failed", "detail": "missing_token"}


# --------------------------------------------------------------------------- message


def test_welcome_text_is_sammichs_current_message():
    lettuce_copy = (SRC / "lettuce" / "messages" / "T04T40NHX-team_join.txt").read_text().strip()
    sammich_copy = (ROOT.parent / "blt-sammich" / "src" / "data" / "message-T04T40NHX-team_join.md")
    if sammich_copy.exists():
        assert lettuce_copy == sammich_copy.read_text().strip()
    # .txt under src/ is what Wrangler bundles as a text module (.md and data/ are not).
    assert wb.MESSAGES_DIR.is_relative_to(SRC)


def test_render_uses_file_mentions_user_and_links_channels():
    text, loaded = wb.render_welcome(OWASP, "U42", [{"id": "C1", "name": "general"}])
    assert loaded
    assert "<@U42>" in text and "{user_id}" not in text
    for channel in ("<#C0C8JS08KN1>", "<#C0AM75HCZU7>", "<#C0C893EJ72T>"):
        assert channel in text
    assert text.endswith(":bar_chart: *Most Active Channels:* *<#C1|general>*")


def test_render_falls_back_when_template_missing():
    text, loaded = wb.render_welcome("TNOFILE", "U42")
    assert not loaded and "<@U42>" in text


def test_welcome_blocks_have_static_logo_and_tracked_footer(db, slack):
    env = make_env(db, WELCOME_ENABLED="true")
    run(wb.accept_team_join(env, None, team_join_body(), OWASP))
    post = [c for c in slack.calls if c["api"] == "chat.postMessage"][0]["body"]
    tid = db.rows("SELECT tracking_id FROM team_joins")[0]["tracking_id"]
    section, footer = post["blocks"]
    assert section["accessory"]["image_url"] == "https://lettuce.owaspblt.org/docs/static/blt-logo.png"
    assert "tid" not in section["accessory"]["image_url"]
    assert footer["elements"][0]["image_url"] == (
        "https://lettuce.owaspblt.org/welcome-logo?tid=" + tid)
    assert "<#C0C8JS08KN1>" in section["text"]["text"]
    assert post["channel"] == "D123"
    assert (ROOT / "public" / "docs" / "static" / "blt-logo.png").exists()


def test_top_channels_from_stats_are_appended(db, slack):
    env = make_env(db, WELCOME_ENABLED="true")
    run(wb.state_put(env, "channels:" + OWASP,
                     {"top": [{"id": "C9", "name": "owasp-community", "members": 9000}]}))
    run(wb.accept_team_join(env, None, team_join_body(), OWASP))
    post = [c for c in slack.calls if c["api"] == "chat.postMessage"][0]["body"]
    assert "*<#C9|owasp-community>*" in post["blocks"][0]["text"]["text"]


# --------------------------------------------------------------------------- tracking


def test_logo_hit_records_first_open_only(db, slack):
    env = make_env(db, WELCOME_ENABLED="true")
    run(wb.accept_team_join(env, None, team_join_body(), OWASP))
    tid = db.rows("SELECT tracking_id FROM team_joins")[0]["tracking_id"]
    resp = run(worker.handle_request(
        get_request("/welcome-logo?tid=" + tid, {"User-Agent": "Slack-ImgProxy (+https://api.slack.com)"}),
        env))
    assert resp.status == 302
    assert resp.headers.get("Location") == "https://lettuce.owaspblt.org/docs/static/blt-logo.png"
    first = db.rows("SELECT opened_at, opened_via FROM team_joins")[0]
    assert first["opened_at"] and first["opened_via"].startswith("slack-imgproxy")
    assert run(wb.record_logo_hit(env, tid, "Slack/1.0")) is False
    assert db.rows("SELECT opened_at, opened_via FROM team_joins")[0] == first


def test_logo_hit_ignores_malformed_ids(db):
    env = make_env(db)
    assert run(wb.record_logo_hit(env, "' OR 1=1 --", "x")) is False
    resp = run(worker.handle_request(get_request("/welcome-logo?tid=nope"), env))
    assert resp.status == 302


# --------------------------------------------------------------------------- admin report


def basic(user, password):
    return "Basic " + base64.b64encode("{0}:{1}".format(user, password).encode()).decode()


def test_admin_report_requires_basic_auth(db):
    env = make_env(db, ADMIN_USERNAME="admin", ADMIN_PASSWORD="pw")
    assert run(worker.handle_request(get_request("/admin/welcomes"), env)).status == 401
    bad = get_request("/admin/welcomes", {"Authorization": basic("admin", "nope")})
    assert run(worker.handle_request(bad, env)).status == 401
    unset = make_env(db)
    good = get_request("/admin/welcomes", {"Authorization": basic("admin", "pw")})
    assert run(worker.handle_request(good, unset)).status == 401  # fails closed


def test_admin_report_counts_and_html(db, slack):
    env = make_env(db, WELCOME_ENABLED="true", ADMIN_USERNAME="admin", ADMIN_PASSWORD="pw")
    run(wb.accept_team_join(env, None, team_join_body("Ev1", "U1"), OWASP))
    run(wb.accept_team_join(env, None, team_join_body("Ev2", "U2", is_bot=True), OWASP))
    slack.queue("conversations.open", (200, {"ok": False, "error": "user_not_found"}))
    run(wb.accept_team_join(env, None, team_join_body("Ev3", "U3"), OWASP))
    tid = db.rows("SELECT tracking_id FROM team_joins WHERE user_id = 'U1'")[0]["tracking_id"]
    run(wb.record_logo_hit(env, tid, "Slack/1"))
    auth = {"Authorization": basic("admin", "pw")}
    resp = run(worker.handle_request(get_request("/admin/welcomes?format=json", auth), env))
    report = json.loads(resp.body)
    week = report["last_7_days"]
    assert (week["joins"], week["eligible"], week["delivered"], week["opened"], week["failed"],
            week["skipped"]) == (3, 2, 1, 1, 1, 1)
    assert week["delivered_pct"] == 50.0 and week["opened_pct"] == 100.0
    html = run(worker.handle_request(get_request("/admin/welcomes", auth), env))
    assert html.status == 200 and "OWASP welcome DM delivery" in html.body
    assert "conversations.open:user_not_found" in html.body


# --------------------------------------------------------------------------- health


NOW = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)


def summary(eligible=0, delivered=0):
    return {"joins": eligible, "eligible": eligible, "delivered": delivered,
            "delivered_pct": wb._pct(delivered, eligible)}


def auth_ok(age_minutes=30, ok=True, error=""):
    return {"value": {"ok": ok, "error": error},
            "updated_at": (NOW - timedelta(minutes=age_minutes)).isoformat()}


def test_health_ok():
    status, body = wb.evaluate_health(True, summary(10, 10), auth_ok(), "t", "t", True, NOW)
    assert status == 200 and body["status"] == wb.HEALTH_OK and body["problems"] == []


def test_health_quiet_day_is_ok():
    status, body = wb.evaluate_health(True, summary(0, 0), auth_ok(), "", "", True, NOW)
    assert status == 200 and body["status"] == wb.HEALTH_OK


def test_health_fails_when_joins_but_no_welcomes():
    status, body = wb.evaluate_health(True, summary(3, 0), auth_ok(), "t", "", True, NOW)
    assert status == 503 and "joins_without_welcomes_24h" in body["problems"]
    assert body["status"] == wb.HEALTH_FAILING


def test_health_fails_on_low_rate():
    status, body = wb.evaluate_health(True, summary(10, 2), auth_ok(), "t", "t", True, NOW)
    assert status == 503 and body["problems"] == ["low_delivery_rate_24h"]


@pytest.mark.parametrize("auth, problem", [
    (None, "slack_auth_never_checked"),
    (auth_ok(ok=False, error="invalid_auth"), "slack_auth_failed:invalid_auth"),
    (auth_ok(age_minutes=60 * 4), "slack_auth_check_stale"),
])
def test_health_fails_on_slack_auth(auth, problem):
    status, body = wb.evaluate_health(True, summary(), auth, "", "", True, NOW)
    assert status == 503 and problem in body["problems"]


def test_health_fails_when_template_missing():
    status, body = wb.evaluate_health(True, summary(), auth_ok(), "", "", False, NOW)
    assert status == 503 and body["problems"] == ["welcome_template_missing"]


def test_health_disabled_is_200_but_lists_problems():
    status, body = wb.evaluate_health(False, summary(5, 0), None, "t", "", True, NOW)
    assert status == 200 and body["status"] == wb.HEALTH_DISABLED
    assert "joins_without_welcomes_24h" in body["problems"]


def test_monitor_keyword_appears_only_when_healthy():
    """blt-monitor's lettuce_owasp_welcome check passes on HTTP 2xx containing this keyword."""
    keyword = "welcome-healthy"
    monitors = json.loads((ROOT.parent / "blt-monitor" / "public" / "monitors.json").read_text()) \
        if (ROOT.parent / "blt-monitor").exists() else []
    for monitor in monitors:
        if monitor["id"] == "lettuce_owasp_welcome":
            assert monitor["keyword"] == keyword
            assert monitor["url"] == "https://lettuce.owaspblt.org/health/welcome"
    _, healthy = wb.evaluate_health(True, summary(1, 1), auth_ok(), "t", "t", True, NOW)
    _, failing = wb.evaluate_health(True, summary(1, 0), auth_ok(), "t", "", True, NOW)
    _, disabled = wb.evaluate_health(False, summary(), auth_ok(), "", "", True, NOW)
    assert keyword in json.dumps(healthy)
    assert keyword not in json.dumps(failing) and keyword not in json.dumps(disabled)


def test_summary_grace_period_ignores_join_still_sending():
    rows = [{"welcome_status": "pending", "joined_at": (NOW - timedelta(minutes=2)).isoformat()},
            {"welcome_status": "pending", "joined_at": (NOW - timedelta(hours=2)).isoformat()}]
    out = wb.summarize_joins(rows, NOW)
    assert out["joins"] == 2 and out["eligible"] == 1 and out["delivered"] == 0


def test_health_endpoint_end_to_end(db, slack):
    env = make_env(db, WELCOME_ENABLED="true")
    resp = run(worker.handle_request(get_request("/health/welcome"), env))
    assert resp.status == 503  # never auth-checked
    run(wb.run_welcome_cron(env))
    run(wb.accept_team_join(env, None, team_join_body(), OWASP))
    resp = run(worker.handle_request(get_request("/health/welcome"), env))
    body = json.loads(resp.body)
    assert resp.status == 200 and body["status"] == "welcome-healthy"
    assert body["last_team_join_at"] and body["last_welcome_delivered_at"]
    assert body["slack_auth"]["ok"] is True
    assert "xoxb" not in resp.body


def test_health_endpoint_fails_when_welcomes_stop(db, slack):
    env = make_env(db, WELCOME_ENABLED="true")
    run(wb.run_welcome_cron(env))
    old = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    db.conn.execute(
        "INSERT INTO team_joins (team_id, user_id, event_id, joined_at, welcome_status) "
        "VALUES (?, 'U9', 'Ev9', ?, 'failed')", [OWASP, old])
    db.conn.commit()
    resp = run(worker.handle_request(get_request("/health/welcome"), env))
    assert resp.status == 503
    assert "joins_without_welcomes_24h" in json.loads(resp.body)["problems"]


# --------------------------------------------------------------------------- cron


def test_cron_auth_test_detects_token_for_other_workspace(db, slack):
    env = make_env(db)
    slack.queue("auth.test", (200, {"ok": True, "team_id": BLT, "user_id": "UBOT"}))
    run(wb.run_welcome_cron(env))
    state = run(wb.state_get(env, "auth:" + OWASP))
    assert state["value"] == {"ok": False, "error": "token_for_other_team"}


def test_cron_refreshes_channel_stats_once_a_day(db, slack):
    env = make_env(db)
    page1 = {"ok": True, "channels": [{"id": "C1", "name": "a", "num_members": 5},
                                      {"id": "C2", "name": "b", "num_members": 50}],
             "response_metadata": {"next_cursor": "next"}}
    page2 = {"ok": True, "channels": [{"id": "C3", "name": "c", "num_members": 20}],
             "response_metadata": {"next_cursor": ""}}
    slack.queue("conversations.list", (200, page1), (200, page2))
    run(wb.run_welcome_cron(env))
    stats = run(wb.state_get(env, "channels:" + OWASP))["value"]
    assert [c["id"] for c in stats["top"]] == ["C2", "C3", "C1"]
    assert stats["channel_count"] == 3 and stats["complete"] is True
    run(wb.run_welcome_cron(env))  # fresh: not refreshed again
    assert slack.apis().count("conversations.list") == 2
    assert slack.apis().count("auth.test") == 2


def test_scheduled_runs_welcome_cron(db):
    env = make_env(db, CRON_SECRET="s")
    entry = worker.Default()
    entry.env = env
    event = worker._CronEvent("0 * * * *", 1760000400000)
    with patch.object(worker.welcome_bot, "run_welcome_cron", new=AsyncMock()) as cron, \
            patch.object(worker, "run_workspace_metrics_sync", new=AsyncMock()), \
            patch.object(worker, "run_inactivity_monitor", new=AsyncMock()):
        run(entry.scheduled(event, env, None))
    cron.assert_awaited_once_with(env)


def test_metrics_sync_skips_welcome_workspace(db):
    db.add_workspace(BLT, "xoxb-blt")
    env = make_env(db)
    with patch.object(worker, "scan_workspace_channels", new=AsyncMock()) as scan, \
            patch.object(worker, "fetch_workspace_member_count", new=AsyncMock(return_value=0)), \
            patch.object(worker, "send_missing_github_org_alert",
                         new=AsyncMock(return_value={"ok": False})) as alert:
        result = run(worker.run_workspace_metrics_sync(env))
    assert result["processed"] == 1
    assert [c.args[2] for c in scan.await_args_list] == ["xoxb-blt"]
    assert all(c.args[1].get("team_id") != OWASP for c in alert.await_args_list)


# --------------------------------------------------------------------------- public stats


def test_community_stats(db, slack):
    env = make_env(db, WELCOME_ENABLED="true")
    run(wb.accept_team_join(env, None, team_join_body("Ev1", "U1"), OWASP))
    run(wb.accept_team_join(env, None, team_join_body("Ev2", "U2"), OWASP))
    run(wb.state_put(env, "channels:" + OWASP,
                     {"top": [{"id": "C1", "name": "general", "members": 99}], "channel_count": 7}))
    resp = run(worker.handle_request(get_request("/api/community-stats"), env))
    body = json.loads(resp.body)
    assert body["joins_last_7_days"] == 2 and body["welcomed_last_30_days"] == 2
    assert len(body["team_join_history"]) == 30
    assert body["channels_with_most_members"] == [{"id": "C1", "name": "general", "members": 99}]
    assert "U1" not in resp.body


def test_unexpected_crash_is_recorded_as_failed(db, slack, monkeypatch):
    env = make_env(db, WELCOME_ENABLED="true")
    monkeypatch.setattr(wb, "render_welcome", Mock(side_effect=KeyError("boom")))
    out = run(wb.accept_team_join(env, None, team_join_body(), OWASP))
    assert out["action"] == "accepted"
    assert db.rows("SELECT welcome_status, detail FROM team_joins")[0] == {
        "welcome_status": "failed", "detail": "crash:KeyError"}
