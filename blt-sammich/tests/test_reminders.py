"""/setreminder: time parsing, limits, list/cancel, the due query plan, delivery and
the /__scheduled endpoint. D1 is stood in by sqlite with every migration applied."""

import asyncio
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src import worker

MIGRATIONS = sorted((Path(__file__).resolve().parents[1] / "migrations").glob("*.sql"))
NOW = int(datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc).timestamp())  # a Monday


def utc(*args):
    return int(datetime(*args, tzinfo=timezone.utc).timestamp())


class _Statement:
    def __init__(self, db, sql):
        self.db, self.sql, self.params = db, sql, ()

    def bind(self, *params):
        self.params = params
        return self

    async def run(self):
        self.db.queries.append(self.sql)
        cursor = self.db.conn.execute(self.sql, self.params)
        rows = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        self.db.conn.commit()
        return {
            "success": True,
            "results": rows,
            "meta": {"changes": 0 if cursor.description else cursor.rowcount, "last_row_id": cursor.lastrowid},
        }


class SqliteD1:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        for path in MIGRATIONS:
            self.conn.executescript(path.read_text())
        self.queries = []

    def prepare(self, sql):
        return _Statement(self, sql)

    def rows(self, sql, params=()):
        return [dict(row) for row in self.conn.execute(sql, params).fetchall()]


class _Env:
    pass


class _Headers(dict):
    def get(self, key, default=None):
        for name, value in self.items():
            if name.lower() == key.lower():
                return value
        return default


class _Request:
    def __init__(self, method, url, headers=None, body=""):
        self.method, self.url, self.headers, self.body = method, url, _Headers(headers or {}), body

    async def text(self):
        return self.body


@pytest.fixture
def env():
    value = _Env()
    value.DB = SqliteD1()
    return value


def run(coro):
    return asyncio.run(coro)


def command(env, text, user="U1", team="T1", now=NOW):
    form = {"command": "/setreminder", "text": text, "team_id": team, "user_id": user, "api_app_id": "A1"}
    return run(worker.setreminder_response(form, env, now=now))


# --- time parsing -------------------------------------------------------------------

PARSE_CASES = [
    # text, tz_offset, expected due_at, expected rest
    ("in 30m stand-up", 0, NOW + 1800, "stand-up"),
    ("in 2h deploy", 0, NOW + 7200, "deploy"),
    ("in 3d review", 0, NOW + 3 * 86400, "review"),
    ("in 1h30m tea", 0, NOW + 5400, "tea"),
    ("in 1 hour and 15 minutes tea", 0, NOW + 4500, "tea"),
    ("in 2 weeks x", 0, NOW + 14 * 86400, "x"),
    ("IN 5 Mins x", 0, NOW + 300, "x"),
    ("tomorrow 9am standup", 0, utc(2026, 10, 20, 9, 0), "standup"),
    ("tomorrow at 14:30 standup", 0, utc(2026, 10, 20, 14, 30), "standup"),
    ("tomorrow standup", 0, utc(2026, 10, 20, 9, 0), "standup"),
    ("today 5pm go home", 0, utc(2026, 10, 19, 17, 0), "go home"),
    ("today noon lunch", 0, utc(2026, 10, 19, 12, 0), "lunch"),
    ("tomorrow 12am x", 0, utc(2026, 10, 20, 0, 0), "x"),
    ("at 14:30 call", 0, utc(2026, 10, 19, 14, 30), "call"),
    ("at 9:15am call", 0, utc(2026, 10, 20, 9, 15), "call"),  # 09:15 passed: tomorrow
    ("at 12:00 call", 0, utc(2026, 10, 20, 12, 0), "call"),  # exactly now: tomorrow
    ("2026-12-01 ship", 0, utc(2026, 12, 1, 9, 0), "ship"),
    ("2026-12-01 14:30 ship", 0, utc(2026, 12, 1, 14, 30), "ship"),
    ("2026-12-01 at 7:05 ship", 0, utc(2026, 12, 1, 7, 5), "ship"),
    ("2026-12-01T14:30Z ship", 7200, utc(2026, 12, 1, 14, 30), "ship"),
    ("2026-12-01T14:30:15+02:00 ship", 0, utc(2026, 12, 1, 12, 30, 15), "ship"),
    ("2026-12-01T14:30-0530 ship", 0, utc(2026, 12, 1, 20, 0), "ship"),
    # The user's Slack time zone: UTC+2 and UTC-5.
    ("at 14:30 call", 7200, utc(2026, 10, 19, 12, 30), "call"),
    ("tomorrow 9am x", -18000, utc(2026, 10, 20, 14, 0), "x"),
    ("2026-12-01 14:30 ship", 3600, utc(2026, 12, 1, 13, 30), "ship"),
    ("in 30m x", 3600, NOW + 1800, "x"),
]


@pytest.mark.parametrize("text,tz_offset,due_at,rest", PARSE_CASES)
def test_parse_reminder_when(text, tz_offset, due_at, rest):
    assert worker.parse_reminder_when(text, NOW, tz_offset) == (due_at, rest)


@pytest.mark.parametrize(
    "text,error",
    [
        ("in", "duration"),
        ("in soon x", "duration"),
        ("in 30mx x", "duration"),
        ("in 0m x", "future"),
        ("today x", "Add a time"),
        ("at 25:00 x", "not a valid time"),
        ("at 13pm x", "not a valid time"),
        ("at 9 x", "couldn't read the time"),
        ("2026-02-30 x", "not a valid date"),
        ("2026-12-01T10:00+15:00 x", "UTC offset"),
        ("next week x", "couldn't read the time"),
        ("", "couldn't read the time"),
    ],
)
def test_parse_reminder_when_errors(text, error):
    with pytest.raises(ValueError, match=error):
        worker.parse_reminder_when(text, NOW, 0)


@pytest.mark.parametrize(
    "raw,clean",
    [
        ("ping <!here> now", "ping @here now"),
        ("ask <@U123|alice> and <@U456>", "ask @alice and @U456"),
        ("see <#C123|general>", "see #general"),
        ("read <https://x.test/a|the doc> and <https://x.test/b>", "read the doc (https://x.test/a) and https://x.test/b"),
        ("<!subteam^S1|@devs> a &amp; b &lt;c&gt;", "@devs a & b <c>"),
        ("tab\tok\x00\x07 end", "tab\tok end"),
    ],
)
def test_clean_reminder_text(raw, clean):
    assert worker.clean_reminder_text(raw) == clean


def test_slack_escape():
    assert worker.slack_escape("<!channel> & <@U1>") == "&lt;!channel&gt; &amp; &lt;@U1&gt;"


@pytest.mark.parametrize(
    "token,target",
    [
        ("me", ("me", "")),
        ("<@U123ABC|alice>", ("user", "U123ABC")),
        ("<@W123>", ("user", "W123")),
        ("<#C123ABC|general>", ("channel", "C123ABC")),
        ("<#G999>", ("channel", "G999")),
        ("#general", ("channel_name", "general")),
        ("@alice", ("user_name", "alice")),
        ("<@lowercase>", None),
        ("in", None),
        ("tomorrow", None),
    ],
)
def test_parse_reminder_target(token, target):
    assert worker.parse_reminder_target(token) == target


# --- the command --------------------------------------------------------------------


def test_create_stores_an_escaped_dm_reminder(env):
    response = command(env, "in 30m deploy <!channel> &amp; &lt;script&gt;")  # as Slack sends it
    assert response["response_type"] == "ephemeral"
    assert "Reminder #1 set for <!date^{0}^".format(NOW + 1800) in response["text"]
    assert "(UTC), to you" in response["text"]
    assert "deploy @channel &amp; &lt;script&gt;" in response["text"]
    rows = env.DB.rows("SELECT * FROM reminders")
    assert len(rows) == 1
    row = rows[0]
    assert (row["team_id"], row["app_id"], row["user_id"]) == ("T1", "A1", "U1")
    assert (row["target_type"], row["target_id"]) == ("user", "U1")
    assert row["message"] == "deploy @channel & <script>"
    assert (row["due_at"], row["status"], row["attempts"], row["created_at"]) == (NOW + 1800, "pending", 0, NOW)


def test_create_uses_the_users_slack_time_zone(env):
    env.DB.conn.execute(
        "INSERT INTO users (slack_user_id, tz, tz_offset, created_at, updated_at) VALUES ('U1', 'Europe/Berlin', 7200, '', '')"
    )
    response = command(env, "at 14:30 call")
    assert "(your Slack time zone)" in response["text"]
    assert env.DB.rows("SELECT due_at FROM reminders")[0]["due_at"] == utc(2026, 10, 19, 12, 30)


def test_create_targets_channel_and_user(env):
    command(env, "<#C777|general> tomorrow 9am release")
    command(env, "<@U222|bob> in 1h review")
    command(env, "<@U1|me> in 1h self")
    command(env, "me in 2h self too")
    rows = env.DB.rows("SELECT target_type, target_id, message FROM reminders ORDER BY id")
    assert rows == [
        {"target_type": "channel", "target_id": "C777", "message": "release"},
        {"target_type": "user", "target_id": "U222", "message": "review"},
        {"target_type": "user", "target_id": "U1", "message": "self"},
        {"target_type": "user", "target_id": "U1", "message": "self too"},
    ]


def test_create_resolves_a_plain_channel_name(env):
    env.DB.conn.execute("INSERT INTO teams (id, team_id, team_name, created_at, updated_at) VALUES (5, 'T1', 'OWASP', '', '')")
    env.DB.conn.execute(
        "INSERT INTO channels (workspace_id, channel_id, channel_name, created_at, updated_at) VALUES (5, 'C555', 'general', '', '')"
    )
    command(env, "#general in 1h hi")
    assert env.DB.rows("SELECT target_id FROM reminders") == [{"target_id": "C555"}]
    response = command(env, "#nowhere in 1h hi")
    assert "I don't know the channel `#nowhere`" in response["text"]
    response = command(env, "@alice in 1h hi")
    assert "couldn't resolve `@alice`" in response["text"]
    assert len(env.DB.rows("SELECT id FROM reminders")) == 1


@pytest.mark.parametrize(
    "text,error",
    [
        ("in 30m", "What should I remind you about?"),
        ("2026-10-18 x", "already passed"),
        ("in 366d x", "365 days"),
        ("2027-10-20 x", "365 days"),
        ("soon x", "couldn't read the time"),
        ("in 1h " + "x" * 1001, "too long"),
    ],
)
def test_create_rejects_bad_input(env, text, error):
    response = command(env, text)
    assert error in response["text"]
    assert response["response_type"] == "ephemeral"
    assert env.DB.rows("SELECT id FROM reminders") == []


def test_365_days_is_allowed(env):
    command(env, "in 365d x")
    assert len(env.DB.rows("SELECT id FROM reminders")) == 1


def test_pending_limit_is_per_user_and_counts_only_pending(env):
    for index in range(20):
        assert "set for" in command(env, "in {0}m n{0}".format(index + 1))["text"]
    response = command(env, "in 1d one too many")
    assert "already have 20 pending reminders" in response["text"]
    assert len(env.DB.rows("SELECT id FROM reminders")) == 20
    # Another user, or the same user id in another workspace, has their own limit.
    assert "set for" in command(env, "in 1d x", user="U2")["text"]
    assert "set for" in command(env, "in 1d x", team="T2")["text"]
    # Sent, failed and cancelled reminders don't count.
    command(env, "cancel 1")
    env.DB.conn.execute("UPDATE reminders SET status = 'sent' WHERE id = 2")
    assert "set for" in command(env, "in 1d a")["text"]
    assert "set for" in command(env, "in 1d b")["text"]
    assert "already have 20" in command(env, "in 1d c")["text"]


def test_list_shows_only_my_pending_reminders_in_due_order(env):
    assert "no pending reminders" in command(env, "list")["text"]
    command(env, "in 2h second &lt;b&gt;")
    command(env, "in 1h first")
    command(env, "<#C9> in 3h third")
    command(env, "in 1h other user", user="U2")
    command(env, "in 4h cancelled")
    command(env, "cancel 5")
    text = command(env, "list")["text"]
    assert "(3/20)" in text
    assert text.index("`#2`") < text.index("`#1`") < text.index("`#3`")
    assert "second &lt;b&gt;" in text
    assert "to <#C9>" in text
    assert "other user" not in text and "cancelled" not in text


def test_cancel_only_my_pending_reminder(env):
    command(env, "in 1h mine")
    command(env, "in 1h theirs", user="U2")
    assert "no pending reminder #2" in command(env, "cancel 2")["text"]
    assert "Cancelled reminder #1." in command(env, "cancel #1")["text"]
    assert "no pending reminder #1" in command(env, "cancel 1")["text"]
    assert "Usage: `/setreminder cancel <id>`" in command(env, "cancel abc")["text"]
    assert env.DB.rows("SELECT id, status FROM reminders ORDER BY id") == [
        {"id": 1, "status": "cancelled"},
        {"id": 2, "status": "pending"},
    ]


def test_help_and_missing_identity(env):
    assert "*Usage:*" in command(env, "")["text"]
    assert "*Usage:*" in command(env, "help")["text"]
    assert "couldn't tell which workspace" in command(env, "in 1h x", user="")["text"]


def test_command_response_routes_setreminder(env):
    form = {"command": "/setreminder", "text": "help", "team_id": "T1", "user_id": "U1"}
    assert "*Usage:*" in run(worker.command_response(form, env))["text"]
    assert "/setreminder" in worker.SUPPORTED_SLACK_COMMANDS
    assert "/setreminder" in worker.available_commands_text()


def test_manifest_registers_setreminder_with_escaping():
    manifest = (Path(__file__).resolve().parents[1] / "manifest.yaml").read_text()
    block = manifest.split("- command: /setreminder", 1)[1].split("- command:", 1)[0]
    assert "url: https://sammich.owaspblt.org/slack/commands/" in block
    assert "should_escape: true" in block


# --- D1 cost: query plans -----------------------------------------------------------


def query_plan(env, sql, params):
    return " | ".join(row["detail"] for row in env.DB.rows("EXPLAIN QUERY PLAN " + sql, params))


def test_due_query_uses_the_status_due_index(env):
    plan = query_plan(env, worker.REMINDER_DUE_QUERY, (NOW, 50))
    assert "USING INDEX idx_reminders_status_due (status=? AND due_at<?)" in plan
    assert "SCAN" not in plan and "TEMP B-TREE" not in plan


def test_per_user_queries_use_the_user_index(env):
    list_plan = query_plan(
        env,
        "SELECT id, target_type, target_id, message, due_at FROM reminders "
        "WHERE team_id = ? AND user_id = ? AND status = 'pending' ORDER BY due_at LIMIT ?",
        ("T1", "U1", 20),
    )
    assert "USING INDEX idx_reminders_team_user_status_due (team_id=? AND user_id=? AND status=?)" in list_plan
    assert "SCAN" not in list_plan and "TEMP B-TREE" not in list_plan
    count_plan = query_plan(
        env,
        "SELECT COUNT(*) FROM reminders WHERE team_id = ? AND user_id = ? AND status = 'pending'",
        ("T1", "U1"),
    )
    assert "COVERING INDEX idx_reminders_team_user_status_due" in count_plan
    tz_plan = query_plan(env, "SELECT tz, tz_offset FROM users WHERE slack_user_id = ? LIMIT 1", ("U1",))
    assert "SEARCH users USING INDEX" in tz_plan


# --- delivery -----------------------------------------------------------------------


@pytest.fixture
def slack(monkeypatch):
    calls = {"posts": [], "tokens": [], "fail": {}}

    async def fake_token(env, team_id="", channel_id="", app_id=""):
        calls["tokens"].append((team_id, app_id))
        return "" if team_id == "T_NOTOKEN" else "xoxb-" + team_id

    async def fake_fetch_json(url, method="GET", headers=None, body=None):
        payload = json.loads(body)
        calls["posts"].append({"url": url, "auth": headers["Authorization"], **payload})
        error = calls["fail"].get(payload["channel"])
        if error:
            return True, {"ok": False, "error": error}, 200
        return True, {"ok": True, "ts": "1.2"}, 200

    monkeypatch.setattr(worker, "workspace_slack_token", fake_token)
    monkeypatch.setattr(worker, "fetch_json", fake_fetch_json)
    return calls


def add(env, team="T1", user="U1", target_type="user", target="U1", message="hi", due=NOW - 60, status="pending"):
    cursor = env.DB.conn.execute(
        "INSERT INTO reminders (team_id, app_id, user_id, target_type, target_id, message, due_at, status, created_at) "
        "VALUES (?, 'A1', ?, ?, ?, ?, ?, ?, ?)",
        (team, user, target_type, target, message, due, status, NOW - 3600),
    )
    env.DB.conn.commit()
    return cursor.lastrowid


def test_delivery_sends_due_reminders_with_each_teams_token(env, slack):
    own = add(env, message="stand-up <!here>")
    channel = add(env, team="T2", user="U5", target_type="channel", target="C9", message="ship")
    later = add(env, due=NOW + 60)
    cancelled = add(env, status="cancelled")

    summary = run(worker.process_due_reminders(env, now=NOW))

    assert summary == {"due": 2, "sent": 2, "retry": 0, "failed": 0}
    posts = {post["channel"]: post for post in slack["posts"]}
    assert set(posts) == {"U1", "C9"}
    assert posts["U1"]["url"] == "https://slack.com/api/chat.postMessage"
    assert posts["U1"]["auth"] == "Bearer xoxb-T1"
    assert posts["U1"]["text"] == ":alarm_clock: *Reminder:* stand-up &lt;!here&gt;"
    assert posts["C9"]["auth"] == "Bearer xoxb-T2"
    assert posts["C9"]["text"] == ":alarm_clock: *Reminder from <@U5>:* ship"
    assert posts["C9"]["unfurl_links"] is False
    assert sorted(slack["tokens"]) == [("T1", "A1"), ("T2", "A1")]
    rows = {row["id"]: row for row in env.DB.rows("SELECT * FROM reminders")}
    assert (rows[own]["status"], rows[own]["attempts"], rows[own]["sent_at"]) == ("sent", 1, NOW)
    assert rows[channel]["status"] == "sent"
    assert rows[later]["status"] == "pending" and rows[later]["attempts"] == 0
    assert rows[cancelled]["status"] == "cancelled"

    # Nothing due: one read, no writes.
    env.DB.queries.clear()
    assert run(worker.process_due_reminders(env, now=NOW)) == {"due": 0, "sent": 0, "retry": 0, "failed": 0}
    assert env.DB.queries == [worker.REMINDER_DUE_QUERY]


def test_delivery_retries_then_marks_failed_after_three_attempts(env, slack):
    slack["fail"]["C404"] = "channel_not_found"
    failing = add(env, target_type="channel", target="C404")
    no_token = add(env, team="T_NOTOKEN")

    for attempt in (1, 2):
        summary = run(worker.process_due_reminders(env, now=NOW + attempt * 300))
        assert summary == {"due": 2, "sent": 0, "retry": 2, "failed": 0}
        row = env.DB.rows("SELECT status, attempts, last_error FROM reminders WHERE id = ?", (failing,))[0]
        assert row == {"status": "pending", "attempts": attempt, "last_error": "channel_not_found"}

    summary = run(worker.process_due_reminders(env, now=NOW + 900))
    assert summary == {"due": 2, "sent": 0, "retry": 0, "failed": 2}
    rows = {row["id"]: row for row in env.DB.rows("SELECT id, status, attempts, last_error FROM reminders")}
    assert rows[failing] == {"id": failing, "status": "failed", "attempts": 3, "last_error": "channel_not_found"}
    assert rows[no_token] == {"id": no_token, "status": "failed", "attempts": 3, "last_error": "missing_slack_token"}
    # A missing token never reaches Slack.
    assert {post["channel"] for post in slack["posts"]} == {"C404"}
    # Failed reminders are not picked up again.
    assert run(worker.process_due_reminders(env, now=NOW + 1200))["due"] == 0


def test_delivery_takes_at_most_fifty_oldest_first(env, slack):
    for index in range(55):
        add(env, message="m{0}".format(index), due=NOW - 1000 + index)
    assert run(worker.process_due_reminders(env, now=NOW))["sent"] == 50
    assert [post["text"].rsplit(" ", 1)[1] for post in slack["posts"]][:2] == ["m0", "m1"]
    assert len(env.DB.rows("SELECT id FROM reminders WHERE status = 'pending'")) == 5
    assert run(worker.process_due_reminders(env, now=NOW))["sent"] == 5


def test_delivery_records_a_network_error(env, monkeypatch):
    async def fake_token(env, team_id="", channel_id="", app_id=""):
        return "xoxb-1"

    async def broken_fetch(*args, **kwargs):
        raise RuntimeError("connection reset")

    monkeypatch.setattr(worker, "workspace_slack_token", fake_token)
    monkeypatch.setattr(worker, "fetch_json", broken_fetch)
    reminder = add(env)
    assert run(worker.process_due_reminders(env, now=NOW))["retry"] == 1
    row = env.DB.rows("SELECT status, attempts, last_error FROM reminders WHERE id = ?", (reminder,))[0]
    assert row == {"status": "pending", "attempts": 1, "last_error": "fetch_error: connection reset"}


# --- POST /__scheduled --------------------------------------------------------------


@pytest.fixture
def responses(monkeypatch):
    monkeypatch.setattr(worker, "json_response", lambda payload, status=200: {"status": status, "payload": payload})


def scheduled(env, method="POST", secret=None):
    headers = {} if secret is None else {"X-BLT-Cron-Secret": secret}
    request = _Request(method, "https://cron.internal/__scheduled", headers=headers, body='{"cron":"4-59/5 * * * *"}')
    return run(worker.handle_request(request, env))


def test_scheduled_requires_the_cron_secret(env, responses, slack):
    add(env)
    assert scheduled(env)["status"] == 403  # CRON_SECRET unset refuses everything
    env.CRON_SECRET = "s3cret"
    assert scheduled(env)["status"] == 403
    assert scheduled(env, secret="wrong")["status"] == 403
    assert scheduled(env, method="GET", secret="s3cret")["status"] == 405
    assert slack["posts"] == []
    assert env.DB.rows("SELECT status FROM reminders") == [{"status": "pending"}]


def test_scheduled_sends_due_reminders(env, responses, slack, monkeypatch):
    env.CRON_SECRET = "s3cret"
    add(env)
    monkeypatch.setattr(worker.time, "time", lambda: NOW)
    response = scheduled(env, secret="s3cret")
    assert response == {"status": 200, "payload": {"ok": True, "reminders": {"due": 1, "sent": 1, "retry": 0, "failed": 0}, "pr_review_nudges": {"due": 0, "nudged": 0}, "event_retention": {"events_deleted": 0, "claims_deleted": 0, "cutoff": "2026-10-05T12:00:00+00:00"}}}
    assert env.DB.rows("SELECT status FROM reminders") == [{"status": "sent"}]


def test_scheduled_path_runs_before_assets():
    toml = (Path(__file__).resolve().parents[1] / "wrangler.toml").read_text()
    assert '"/__scheduled"' in toml.split("run_worker_first", 1)[1].split("\n", 1)[0]
