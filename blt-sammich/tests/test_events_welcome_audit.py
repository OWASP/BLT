"""Event log policy, retention, team_join dedupe, the OWASP welcome text and the Slack app audit."""

import asyncio
import json
import re
from datetime import datetime, timezone

from src import worker
from tests.test_reminders import SqliteD1, _Env, _Request


def run(coro):
    return asyncio.run(coro)


def sqlite_env(**values):
    env = _Env()
    env.DB = SqliteD1()
    for key, value in values.items():
        setattr(env, key, value)
    return env


def insert_event(env, event_type, created_at, event_id=""):
    env.DB.conn.execute(
        "INSERT INTO events (workspace_id, event_type, created_at, webhook_event_id) VALUES (1, ?, ?, ?)",
        (event_type, created_at, event_id),
    )
    env.DB.conn.commit()


# --- welcome message ------------------------------------------------------------------

# Channel ids checked against the OWASP workspace's conversations.list on 2026-10-20; the
# #welcome, #announce and *-discussion channels were created by a workspace owner on 2026-10-12.
OWASP_WELCOME_CHANNELS = {
    "C0C8JS08KN1": "welcome",
    "C0AM75HCZU7": "introductions",
    "C0C893EJ72T": "announce",
    "C0C8J92K5FD": "general-discussion",
    "C0C893619LP": "projects-discussion",
    "C0C8Q9H3K5Y": "career-discussion",
    "C0Y12A3FC": "jobs",
    "C0C9JSSR8QY": "offtopic-discussion",
    "C2FF0UVHU": "project-blt",
    "C1WAV9UKY": "chapter-london",
    "C04DH8HEPTR": "contribute",
    "C0B9MNHP1V3": "new-project",
    "C66R5JF6V": "leaders",
    "CFJLZNFN1": "gsoc",
    "C06RS61PH1A": "newsroom",
    "C01P7RH28A1": "amplify",
    "C0C8U858R60": "blogs-and-articles",
    "C0C7KDXJXPX": "shameless-plugs",
    "C038H9GURJ7": "external-activities",
    "C0C8U73TLP6": "owasp-support",
    "C0C89CQ7TPZ": "content-moderation-public",
    "C04T2N9US": "learning",
}


def test_owasp_welcome_message_renders_with_current_channels():
    message = worker.render_team_join_message({"user": {"id": "UNEW", "name": "newbie"}}, "T04T40NHX")

    assert message.startswith(":tada: *Welcome to the OWASP Slack Community, <@UNEW>!* :tada:")
    assert "{" not in message and "}" not in message  # every placeholder filled
    mentioned = re.findall(r"<#(C[A-Z0-9]+)>", message)
    assert set(mentioned) == set(OWASP_WELCOME_CHANNELS)  # only verified channel ids, all of them
    assert not worker.channel_names_mentioned(message.replace("*#project-*", "").replace("*#chapter-*", ""))
    assert "<https://contact.owasp.org>" in message
    # Slack rejects a section block over 3000 characters; leave room for the popular channels.
    assert len(message) < 2600


def test_owasp_welcome_message_has_one_source():
    template = (worker.ROOT_DIR / "data" / "message-T04T40NHX-team_join.md").read_text().strip()
    assert worker.get_workspace_welcome_message("T04T40NHX") == template
    assert not hasattr(worker, "TEAM_WELCOME_MESSAGES")


# --- event log policy -----------------------------------------------------------------


def test_event_log_level_defaults_to_joins():
    env = _Env()
    assert worker.event_log_level(env) == "joins"
    assert worker.should_log_event(env, "Team_Join")
    assert worker.should_log_event(env, "Team_Join_Welcome", "skipped")
    assert worker.should_log_event(env, "Channel_Join_Message")
    assert worker.should_log_event(env, "oauth_callback")
    for diagnostic in ("Message", "app_home_opened", "Slack_API_Response", "Command", "Interaction"):
        assert not worker.should_log_event(env, diagnostic)
    assert worker.should_log_event(env, "Slack_API_Response", "error")  # failures are kept
    env.EVENT_LOG_LEVEL = "ALL"
    assert worker.should_log_event(env, "Message")


def test_record_activity_skips_diagnostic_events_without_touching_d1():
    env = sqlite_env()
    payload = {"type": "event_callback", "team_id": "T1", "event": {"type": "message", "user": "U1", "channel": "C1"}}
    run(worker.record_activity(env, "event", payload))
    run(worker.record_activity(env, "slash_command", {"command": "/stats", "team_id": "T1", "user_id": "U1"}))
    assert env.DB.queries == []


def test_db_log_event_keeps_feature_rows_and_failures_only():
    env = sqlite_env()
    run(worker.db_log_event(env, 1, "Channel_Join", user_slack_id="U1"))
    run(worker.db_log_event(env, 1, "Slack_API_Response", status="success"))
    run(worker.db_log_event(env, 1, "Slack_API_Response", status="error"))
    run(worker.db_log_event(env, 1, "Team_Join_Welcome", status="success", webhook_event_id="Ev1"))
    rows = env.DB.rows("SELECT event_type, status FROM events ORDER BY id")
    assert rows == [
        {"event_type": "Slack_API_Response", "status": "error"},
        {"event_type": "Team_Join_Welcome", "status": "success"},
    ]


def test_slack_response_summary_drops_the_echoed_message():
    response = {"ok": True, "ts": "1.2", "channel": "D1", "message": {"blocks": [{"text": "x" * 5000}]}}
    assert worker.slack_response_summary(response) == {"ok": True, "ts": "1.2", "channel": "D1"}
    assert worker.slack_response_summary({"ok": False, "error": "not_in_channel"}) == {
        "ok": False,
        "error": "not_in_channel",
    }


def test_event_channel_mention_does_not_reset_synced_channel_metadata():
    env = sqlite_env(EVENT_LOG_LEVEL="all")
    env.DB.conn.execute(
        "INSERT INTO channels (workspace_id, team_id, channel_id, channel_name, member_count, purpose, created_at, updated_at) "
        "VALUES (1, 'T1', 'C1', 'contribute', 2281, 'Start here', 'x', 'x')"
    )
    env.DB.conn.commit()
    run(worker.db_ensure_channel(env, 1, "C1", "C1", team_id="T1"))
    run(worker.db_ensure_channel(env, 1, "C2", "C2", team_id="T1"))
    rows = env.DB.rows("SELECT channel_id, channel_name, member_count, purpose FROM channels ORDER BY channel_id")
    assert rows[0] == {"channel_id": "C1", "channel_name": "contribute", "member_count": 2281, "purpose": "Start here"}
    assert rows[1]["channel_id"] == "C2"


# --- retention --------------------------------------------------------------------------

TOP_OF_HOUR = datetime(2026, 10, 20, 13, 4, tzinfo=timezone.utc)


def test_prune_event_log_deletes_old_diagnostic_rows_in_batches():
    env = sqlite_env(EVENT_RETENTION_BATCH="2")
    for _ in range(3):
        insert_event(env, "Message", "2026-09-01T00:00:00+00:00")
    insert_event(env, "Slack_API_Response", "2026-10-19T00:00:00+00:00")  # recent: kept
    insert_event(env, "Team_Join", "2026-01-01T00:00:00+00:00")  # feature row: kept
    insert_event(env, "Team_Join_Welcome", "2026-01-01T00:00:00+00:00")
    env.DB.conn.execute(
        "INSERT INTO slack_event_claims (event_id, created_at) VALUES ('EvOld', '2026-10-17T00:00:00+00:00'), "
        "('EvNew', '2026-10-20T12:00:00+00:00')"
    )
    env.DB.conn.commit()

    first = run(worker.prune_event_log(env, now=TOP_OF_HOUR))
    assert first["events_deleted"] == 2 and first["claims_deleted"] == 1
    assert run(worker.prune_event_log(env, now=TOP_OF_HOUR))["events_deleted"] == 1
    assert run(worker.prune_event_log(env, now=TOP_OF_HOUR))["events_deleted"] == 0
    left = env.DB.rows("SELECT event_type FROM events ORDER BY id")
    assert [row["event_type"] for row in left] == ["Slack_API_Response", "Team_Join", "Team_Join_Welcome"]
    assert env.DB.rows("SELECT event_id FROM slack_event_claims") == [{"event_id": "EvNew"}]


def test_prune_event_log_runs_once_an_hour_and_can_be_disabled():
    env = sqlite_env()
    assert run(worker.prune_event_log(env, now=TOP_OF_HOUR.replace(minute=9))) == {"skipped": "not_top_of_hour"}
    env.EVENT_RETENTION_DAYS = "0"
    assert run(worker.prune_event_log(env, now=TOP_OF_HOUR)) == {"skipped": "disabled"}
    assert env.DB.queries == []


# --- team_join delivery ------------------------------------------------------------------


class _Ctx:
    def __init__(self):
        self.tasks = []

    def waitUntil(self, task):
        self.tasks.append(task)


def team_join_payload(event_id="EvJOIN1"):
    return {
        "type": "event_callback",
        "team_id": "T04T40NHX",
        "event_id": event_id,
        "event": {"type": "team_join", "user": {"id": "UNEW", "team_id": "T04T40NHX"}},
    }


def test_db_claim_slack_event_is_true_once():
    env = sqlite_env()
    assert run(worker.db_claim_slack_event(env, "Ev1", "T1", "team_join")) is True
    assert run(worker.db_claim_slack_event(env, "Ev1", "T1", "team_join")) is False
    assert run(worker.db_claim_slack_event(env, "", "T1", "team_join")) is True  # no id: can't dedupe


def test_team_join_retry_sends_one_welcome(monkeypatch):
    env = sqlite_env()
    calls = []

    async def fake_record(env_, kind, payload):
        calls.append(("record", payload["event_id"]))

    async def fake_welcome(env_, event, team_id="", envelope=None):
        calls.append(("welcome", envelope["event_id"]))
        return {"ok": True, "action": "team_join_welcome_sent"}

    monkeypatch.setattr(worker, "record_activity", fake_record)
    monkeypatch.setattr(worker, "handle_team_join_event", fake_welcome)
    monkeypatch.setattr(worker, "json_response", lambda payload, status=200: payload)

    async def deliver_twice():
        ctx = _Ctx()
        first = await worker.accept_team_join_delivery(env, ctx, team_join_payload())
        # Slack's retry lands while the first delivery's welcome is still pending.
        retry = await worker.accept_team_join_delivery(env, ctx, team_join_payload(), retry_num="1")
        assert calls == []  # nothing ran before the response
        await asyncio.gather(*ctx.tasks)
        return first, retry

    first, retry = run(deliver_twice())
    assert first == {"ok": True, "action": "team_join_accepted"}
    assert retry == {"ok": True, "action": "duplicate_team_join_delivery"}
    assert calls == [("record", "EvJOIN1"), ("welcome", "EvJOIN1")]


def test_team_join_is_answered_before_the_welcome_is_sent(monkeypatch):
    """/slack/events hands team_join to accept_team_join_delivery after the signature check."""
    env = sqlite_env(SLACK_SIGNING_SECRET="secret")
    seen = []

    async def fake_accept(env_, ctx, payload, retry_num=""):
        seen.append((payload["event_id"], retry_num))
        return {"ok": True}

    async def fake_record(*args, **kwargs):
        raise AssertionError("team_join must not be recorded before the response")

    monkeypatch.setattr(worker, "accept_team_join_delivery", fake_accept)
    monkeypatch.setattr(worker, "record_activity", fake_record)
    monkeypatch.setattr(worker, "verify_slack_signature", lambda *args: True)
    body = json.dumps(team_join_payload("EvJOIN2"))
    request = _Request(
        "POST",
        "https://sammich.owaspblt.org/slack/events",
        headers={"content-type": "application/json", "X-Slack-Retry-Num": "2"},
        body=body,
    )
    assert run(worker.handle_request(request, env)) == {"ok": True}
    assert seen == [("EvJOIN2", "2")]


# --- Slack app audit ----------------------------------------------------------------------

PANINI_APPS = [
    {"app_name": "GitHub", "security_rating": "A", "data_access": "Low", "source_url": "https://slack.com/apps/A01BP7R4KNY-github"},
    {"app_name": "Zapier", "security_rating": "C", "data_access": "High", "source_url": "https://slack.com/apps/A024R9PQM-zapier"},
    {"app_name": "Zoom", "security_rating": "B", "source_url": "https://slack.com/apps/A5GE9BMQC-zoom"},
]
PANINI_BANNED = [
    {"fields": {"app_name": "Zoom", "country_name": "Taiwan", "ban_reason": "Government use", "is_active": True}},
    {"fields": {"app_name": "Zoom", "country_name": "Germany", "ban_reason": "Old ban", "is_active": False}},
]


def bot(user_id, name, app_id="", **extra):
    member = {"id": user_id, "real_name": name, "is_bot": True, "updated": 1760000000, "profile": {"api_app_id": app_id, "bot_id": "B" + user_id}}
    member.update(extra)
    return member


def test_slack_app_audit_entry_classifies_apps():
    indexes = worker.build_panini_indexes(PANINI_APPS, PANINI_BANNED)
    now = 1761000000

    def entry(member):
        return worker.slack_app_audit_entry(member, indexes, ("A089A036135",), now_ts=now)

    assert entry({"id": "UHUMAN", "real_name": "Person", "profile": {}}) is None
    assert entry({"id": "USLACKBOT", "is_bot": False, "is_app_user": False, "real_name": "Slackbot"}) is None

    github = entry(bot("U1", "GitHub", "A01BP7R4KNY"))
    assert github["risk"] == "low" and github["catalog"]["security_rating"] == "A" and github["flags"] == []

    zoom = entry(bot("U2", "Zoom", "A5GE9BMQC"))
    assert zoom["risk"] == "high" and "banned" in zoom["flags"]
    assert zoom["banned"]["countries"] == ["Taiwan"]  # inactive bans ignored

    assert entry(bot("U3", "Zapier", "A024R9PQM"))["risk"] == "medium"  # rating C
    unknown = entry(bot("U4", "Harvester 3000", "A0ZZZZZZZ1"))
    assert unknown["risk"] == "medium" and unknown["flags"] == ["unknown"]
    legacy = entry(bot("U5", "adz", "A00"))
    assert legacy["risk"] == "high" and legacy["kind"] == "legacy_bot" and "legacy_bot" in legacy["flags"]
    assert "test_app" in entry(bot("U6", "Demo App", "A0Y"))["flags"]
    workflow = entry(bot("U7", "Welcome message", "A0W", is_workflow_bot=True))
    assert workflow["kind"] == "workflow" and workflow["risk"] == "low"
    assert entry(bot("U8", "OWASP BLT bot", "A089A036135"))["risk"] == "ours"
    assert entry(bot("U9", "Old thing", "A0V", deleted=True))["risk"] == "inactive"
    assert "stale" in entry(bot("U10", "Ancient", "A01BP7R4KNY", updated=1500000000))["flags"]


def test_slack_apps_audit_page_reads_users_list(monkeypatch):
    requests = []

    async def fake_token(env, team_id="", channel_id="", app_id=""):
        return "xoxb-test"

    async def fake_workspace(env, team_id):
        return {"id": 15, "team_id": team_id, "app_id": "A089A036135"}

    async def fake_lists(env):
        indexes = worker.build_panini_indexes(PANINI_APPS, PANINI_BANNED)
        indexes["counts"] = {"catalog": 3, "banned": 2}
        return indexes

    async def fake_scopes(token):
        return ["chat:write", "users:read"]

    async def fake_fetch_json(url, method="GET", headers=None, body=None):
        requests.append((method, url))
        if "cursor=" not in url:
            return True, {"ok": True, "members": [bot("U1", "GitHub", "A01BP7R4KNY"), {"id": "UH", "profile": {}}], "response_metadata": {"next_cursor": "c2"}}, 200
        return True, {"ok": True, "members": [bot("U2", "Zoom", "A5GE9BMQC")], "response_metadata": {"next_cursor": ""}}, 200

    monkeypatch.setattr(worker, "db_get_workspace_bot_token", fake_token)
    monkeypatch.setattr(worker, "db_get_workspace_by_team", fake_workspace)
    monkeypatch.setattr(worker, "load_panini_lists", fake_lists)
    monkeypatch.setattr(worker, "slack_token_scopes", fake_scopes)
    monkeypatch.setattr(worker, "fetch_json", fake_fetch_json)

    result = run(worker.slack_apps_audit_page(_Env(), "T04T40NHX"))
    assert result["ok"] and result["members_scanned"] == 3 and result["next_cursor"] == ""
    assert [app["name"] for app in result["apps"]] == ["GitHub", "Zoom"]
    assert result["own_token_scopes"] == ["chat:write", "users:read"]
    assert all(method == "GET" and "users.list" in url for method, url in requests)  # read-only


def test_slack_apps_audit_requires_admin_auth():
    env = _Env()
    env.ADMIN_URL = "/admin-x"
    env.ADMIN_USERNAME, env.ADMIN_PASSWORD = "admin", "pw"
    original = worker.basic_auth_response
    worker.basic_auth_response = lambda: "auth-required"
    try:
        request = _Request("GET", "https://sammich.owaspblt.org/admin-x?view=slack-apps&format=json")
        assert run(worker.handle_admin_get(request, env)) == "auth-required"
    finally:
        worker.basic_auth_response = original


def test_slack_apps_audit_page_html_escapes_and_loads_json():
    env = _Env()
    env.ADMIN_URL = "/admin-x"
    html = worker.render_slack_apps_audit_html(env, "T04T40NHX")
    assert '"/admin-x?view=slack-apps&format=json&team_id=T04T40NHX"' in html
    assert "textContent" in html and "innerHTML" not in html
