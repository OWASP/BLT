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
