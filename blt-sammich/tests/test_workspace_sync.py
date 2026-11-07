"""Workspace names and counts on the public page: events don't overwrite a stored name with
the team id, and sync_workspace_details fills names, icons and counts from Slack."""

import json
from urllib.parse import parse_qs, urlparse

import pytest

from src import worker
from tests.test_reminders import SqliteD1, _Env, run

OWASP_CHANNELS = [
    {"id": "C1", "name": "owasp-community", "is_general": True, "num_members": 46502, "context_team_id": "T1"},
    {"id": "C2", "name": "project-blt", "num_members": 900, "context_team_id": "T1"},
    {"id": "C3", "name": "secret", "is_private": True, "num_members": 5, "context_team_id": "T1"},
    {"id": "C4", "name": "old", "is_archived": True, "num_members": 50, "context_team_id": "T1"},
]


@pytest.fixture
def env():
    value = _Env()
    value.DB = SqliteD1()
    return value


def add_team(env, team_id, name, app_id="A1"):
    env.DB.conn.execute(
        "INSERT INTO teams (team_id, team_name, app_id, created_at, updated_at) VALUES (?, ?, ?, '', '')",
        (team_id, name, app_id),
    )
    env.DB.conn.commit()


def add_app(env, token, app_id="A1"):
    env.DB.conn.execute(
        "INSERT INTO slack_apps (app_id, bot_token, created_at, updated_at) VALUES (?, ?, '', '')", (app_id, token)
    )
    env.DB.conn.commit()


def teams(env):
    return env.DB.rows(
        "SELECT team_id, team_name, icon_url, channel_count, member_count FROM teams ORDER BY team_id"
    )


@pytest.fixture
def slack(monkeypatch):
    """A Slack whose token xoxb-T1 belongs to team T1 and can read every team's team.info but
    only T1's channels, the way one app token behaves across an org."""
    calls = []

    async def fake_fetch_json(url, method="GET", headers=None, body=None):
        parsed = urlparse(url)
        api = parsed.path.rsplit("/", 1)[-1]
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        token = headers["Authorization"].split(" ", 1)[1]
        calls.append((api, token, query))
        token_team = token.split("-", 1)[1]
        if api == "auth.test":
            return True, {"ok": True, "team_id": token_team}, 200
        if api == "team.info":
            names = {"T1": "OWASP", "T2": "OWASP BLT"}
            team = query["team"]
            return True, {"ok": True, "team": {"id": team, "name": names[team], "icon": {"image_132": "https://icon/" + team}}}, 200
        if api == "conversations.list":
            # Each token lists its own team's channels, whatever team_id is asked for.
            channels = [dict(c, context_team_id=token_team) for c in OWASP_CHANNELS]
            if query.get("cursor") != "next":
                return True, {"ok": True, "channels": channels[:2], "response_metadata": {"next_cursor": "next"}}, 200
            return True, {"ok": True, "channels": channels[2:], "response_metadata": {"next_cursor": ""}}, 200
        raise AssertionError(url)

    monkeypatch.setattr(worker, "fetch_json", fake_fetch_json)
    return calls


def test_event_without_a_team_name_keeps_the_stored_name(env):
    add_team(env, "T1", "OWASP")
    run(worker.db_upsert_workspace(env, team_id="T1", team_name="T1", app_id="A1"))
    run(worker.db_upsert_workspace(env, team_id="T1", team_name="", app_id="A1"))
    assert teams(env)[0]["team_name"] == "OWASP"
    run(worker.db_upsert_workspace(env, team_id="T1", team_name="OWASP Foundation", app_id="A1"))
    assert teams(env)[0]["team_name"] == "OWASP Foundation"


def test_new_team_without_a_name_starts_with_its_id(env):
    run(worker.db_upsert_workspace(env, team_id="T9", team_name="", app_id="A1"))
    assert teams(env)[0]["team_name"] == "T9"


def test_counts_are_open_public_channels_and_general_members():
    channels = OWASP_CHANNELS + [
        {"id": "D1", "is_im": True},
        {"id": "G1", "is_mpim": True},
        {"id": "C9", "is_general": True, "num_members": 7, "context_team_id": "T2"},
    ]
    assert worker.slack_team_counts(channels, "T1") == {"channel_count": 2, "member_count": 46502}
    assert worker.slack_team_counts(channels, "T2") == {"channel_count": 1, "member_count": 7}


def test_sync_names_every_team_and_counts_the_tokens_own(env, slack):
    add_team(env, "T1", "T1")
    add_team(env, "T2", "T2")
    add_app(env, "xoxb-T1")
    env.DB.conn.execute("UPDATE teams SET channel_count = 3, member_count = 4 WHERE team_id = 'T2'")
    env.DB.conn.commit()
    summary = run(worker.sync_workspace_details(env))
    assert summary == {"workspaces": 2, "named": 2, "counted": 1, "subrequests": 5}
    assert teams(env) == [
        {"team_id": "T1", "team_name": "OWASP", "icon_url": "https://icon/T1", "channel_count": 2, "member_count": 46502},
        # The token can't see T2's channels, so T2 keeps the counts it had.
        {"team_id": "T2", "team_name": "OWASP BLT", "icon_url": "https://icon/T2", "channel_count": 3, "member_count": 4},
    ]


def test_sync_counts_a_team_with_its_own_env_token(env, slack, monkeypatch):
    add_team(env, "T2", "T2")
    add_app(env, "xoxb-T1")
    env.SLACK_BOT_TOKEN = "xoxb-T2"
    run(worker.sync_workspace_details(env))
    assert [c[1] for c in slack if c[0] == "conversations.list"] == ["xoxb-T2", "xoxb-T2"]
    assert teams(env)[0]["channel_count"] == 2


def test_sync_stops_at_its_subrequest_budget(env, slack):
    add_team(env, "T1", "T1")
    add_app(env, "xoxb-T1")
    summary = run(worker.sync_workspace_details(env, budget=3))
    assert summary["subrequests"] == 3
    assert summary["counted"] == 0  # a partial channel list never overwrites the counts
    assert teams(env)[0]["channel_count"] == 0
    assert teams(env)[0]["team_name"] == "OWASP"


def test_sync_keeps_an_existing_icon(env, slack):
    add_team(env, "T1", "T1")
    add_app(env, "xoxb-T1")
    env.DB.conn.execute("UPDATE teams SET icon_url = 'https://mine' WHERE team_id = 'T1'")
    env.DB.conn.commit()
    run(worker.sync_workspace_details(env))
    assert teams(env)[0]["icon_url"] == "https://mine"


def test_install_does_not_reset_counts(env):
    add_team(env, "T1", "OWASP")
    env.DB.conn.execute("UPDATE teams SET channel_count = 9, member_count = 99")
    env.DB.conn.commit()
    run(worker.upsert_connected_workspace(env, "T1", "OWASP"))
    assert teams(env)[0]["channel_count"] == 9
    assert teams(env)[0]["member_count"] == 99


def test_public_api_shows_synced_names_and_counts(env, slack):
    add_team(env, "T1", "T1")
    add_app(env, "xoxb-T1")
    run(worker.sync_workspace_details(env))
    row = run(worker.db_list_workspaces_public(env))[0]
    assert (row["team_name"], row["channel_count"], row["member_count"]) == ("OWASP", 2, 46502)
    json.dumps(row)


# --- workspace dashboard ------------------------------------------------------------

DAY = 86400
NOW_TS = 1_800_000_000  # 2027-01-15


def test_channel_stats_rank_top_channels_and_find_fun_facts():
    channels = [
        {"id": "C1", "name": "general", "is_general": True, "num_members": 500, "created": NOW_TS - 3000 * DAY,
         "purpose": {"value": "Everyone"}},
        {"id": "C2", "name": "project-a", "num_members": 40, "created": NOW_TS - 10 * DAY},
        {"id": "C3", "name": "project-b", "num_members": 2, "created": NOW_TS - 400 * DAY, "topic": {"value": "B"}},
        {"id": "C4", "name": "project-c", "num_members": 1, "created": NOW_TS - 20 * DAY},
        {"id": "C5", "name": "chapter-x", "num_members": 60, "created": NOW_TS - 5 * DAY},
        {"id": "C6", "name": "secret", "is_private": True, "num_members": 999, "created": NOW_TS},
        {"id": "C7", "name": "elsewhere", "num_members": 999, "context_team_id": "T2"},
    ] + [{"id": "CX{0}".format(i), "name": "x{0}".format(i), "num_members": 3} for i in range(12)]
    stats = worker.slack_channel_stats(channels, "T1", now=NOW_TS)
    assert [c["name"] for c in stats["top"][:3]] == ["general", "chapter-x", "project-a"]
    assert len(stats["top"]) == 10
    assert stats["top"][0] == {"id": "C1", "name": "general", "members": 500, "created": NOW_TS - 3000 * DAY, "purpose": "Everyone"}
    assert stats["oldest"]["name"] == "general"
    assert [c["name"] for c in stats["newest"]][:3] == ["chapter-x", "project-a", "project-c"]
    assert stats["created_last_year"] == 3
    assert stats["families"] == [{"prefix": "project", "channels": 3}]
    assert stats["quiet"] == 2
    assert stats["median_members"] == 3
    assert stats["described"] == 2
    assert stats["total"] == 17


def add_event(env, workspace_id, event_type, created_at, opened_at="", opened_via=""):
    env.DB.conn.execute(
        "INSERT INTO events (workspace_id, event_type, created_at, opened_at, opened_via) VALUES (?, ?, ?, ?, ?)",
        (workspace_id, event_type, created_at, opened_at, opened_via),
    )
    env.DB.conn.commit()


def test_activity_stats_count_joins_zones_and_welcome_opens(env):
    add_team(env, "T1", "OWASP")
    for stamp in ["2026-06-01T09:10:00+00:00", "2026-06-01T09:50:00+00:00", "2026-06-01T15:00:00+00:00",
                  "2026-06-03T09:00:00+00:00"]:
        add_event(env, 1, "Team_Join", stamp)
    add_event(env, 1, "Team_Join_Welcome", "2026-06-01T09:11:00+00:00", "x", "slack-client: iPhone")
    add_event(env, 1, "Team_Join_Welcome", "2026-06-01T09:12:00+00:00", "x", "slack-imgproxy: Slack-ImgProxy")
    add_event(env, 1, "Team_Join_Welcome", "2026-06-01T09:13:00+00:00")
    for i, tz in enumerate(["Asia/Kolkata", "Asia/Kolkata", "Europe/Berlin", ""]):
        env.DB.conn.execute(
            "INSERT INTO users (slack_user_id, team_id, tz, created_at, updated_at) VALUES (?, 'T1', ?, '', '')",
            ("U{0}".format(i), tz),
        )
    env.DB.conn.commit()
    stats = run(worker.db_workspace_activity_stats(env, 1, "T1"))
    assert stats["joins"] == 4
    assert stats["tracking_since"] == "2026-06-01"
    assert stats["record_day"] == {"day": "2026-06-01", "joins": 3}
    assert stats["joins_by_weekday"] == [3, 0, 1, 0, 0, 0, 0]  # 2026-06-01 is a Monday
    assert stats["joins_by_hour_utc"][9] == 3 and stats["joins_by_hour_utc"][15] == 1
    assert stats["time_zones"] == [{"tz": "Asia/Kolkata", "people": 2}, {"tz": "Europe/Berlin", "people": 1}]
    assert (stats["time_zone_count"], stats["people_with_time_zone"]) == (2, 3)
    assert (stats["welcome_sent"], stats["welcome_opened"], stats["welcome_opened_in_app"]) == (3, 2, 1)


def test_sync_stores_dashboard_stats(env, slack):
    add_team(env, "T1", "T1")
    add_team(env, "T2", "T2")
    add_app(env, "xoxb-T1")
    add_event(env, 1, "Team_Join", "2026-06-01T09:10:00+00:00")
    run(worker.sync_workspace_details(env))
    owasp = json.loads(env.DB.rows("SELECT stats_json FROM teams WHERE team_id = 'T1'")[0]["stats_json"])
    assert [c["name"] for c in owasp["channels"]["top"]] == ["owasp-community", "project-blt"]
    assert owasp["activity"]["joins"] == 1
    assert owasp["updated_at"]
    # No token of its own: activity and team facts, but no channel stats.
    blt = json.loads(env.DB.rows("SELECT stats_json FROM teams WHERE team_id = 'T2'")[0]["stats_json"])
    assert "channels" not in blt and blt["activity"]["joins"] == 0


def test_dashboard_api_returns_one_workspace(env, slack, monkeypatch):
    monkeypatch.setattr(worker, "json_response", lambda payload, status=200: {"status": status, "payload": payload})
    add_team(env, "T1", "T1")
    add_app(env, "xoxb-T1")
    run(worker.sync_workspace_details(env))

    class Request:
        method = "GET"
        headers = {}

        def __init__(self, url):
            self.url = url

    response = run(worker.handle_request(Request("https://sammich.owaspblt.org/api/workspaces/T1"), env))
    assert response["status"] == 200
    workspace = response["payload"]["workspace"]
    assert (workspace["team_name"], workspace["channel_count"], workspace["member_count"]) == ("OWASP", 2, 46502)
    assert workspace["stats"]["channels"]["top"][0]["name"] == "owasp-community"
    assert len(workspace["team_join_history"]) == 30
    assert "bot_token" not in json.dumps(workspace) and "stats_json" not in workspace
    missing = run(worker.handle_request(Request("https://sammich.owaspblt.org/api/workspaces/T404"), env))
    assert missing["status"] == 404
    bad = run(worker.handle_request(Request("https://sammich.owaspblt.org/api/workspaces/x' OR 1"), env))
    assert bad["status"] == 404


def test_homepage_links_each_workspace_to_its_dashboard():
    from pathlib import Path

    public = Path(__file__).resolve().parents[1] / "public"
    index = (public / "index.html").read_text()
    assert '"/workspace?team=" + encodeURIComponent(workspace.team_id' in index
    assert "${dashboard}#channels" in index
    page = (public / "workspace.html").read_text()
    assert "/api/workspaces/" in page and 'id="top-channels"' in page
