import base64
import asyncio
from pathlib import Path

from src import worker


def test_verify_slack_signature_accepts_valid_request():
    secret = "signing-secret"
    timestamp = "1710000000"
    body = "token=value&command=%2Fproject"
    import hashlib
    import hmac

    expected = (
        "v0="
        + hmac.new(
            secret.encode("utf-8"),
            "v0:{0}:{1}".format(timestamp, body).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    )

    assert worker.verify_slack_signature(
        secret, timestamp, body, expected, now_ts=1710000000
    )


def test_verify_slack_signature_rejects_expired_request():
    assert not worker.verify_slack_signature(
        "secret",
        "1710000000",
        "body",
        "v0=invalid",
        now_ts=1710000601,
    )


def test_project_response_without_query_returns_blocks():
    response = worker.project_response("")
    assert response["blocks"]
    assert response["text"] == "Choose a project to inspect."


def test_repo_response_without_query_returns_blocks():
    response = worker.repo_response("")
    assert response["blocks"]
    assert response["text"] == "Choose a technology to inspect."


def test_interaction_response_returns_project_detail():
    response = worker.interaction_response(
        {
            "actions": [
                {
                    "action_id": "project_select_action_0",
                    "selected_option": {"value": "www-project-zap"},
                }
            ]
        }
    )
    assert "www-project-zap" in response["text"]


def test_build_blocks_are_chunked_and_capped():
    project_blocks = worker.build_project_selection_blocks(
        ["project-{0}".format(index) for index in range(201)]
    )
    assert len(project_blocks) == 3

    repo_blocks = worker.build_repo_selection_blocks(
        {"python": ["https://example.com"]}
    )
    assert len(repo_blocks) == 2


def test_summarize_contributors_sorts_by_total_activity():
    rows = worker.summarize_contributors(
        [{"user": {"login": "alice"}}, {"user": {"login": "alice"}}],
        [{"user": {"login": "bob"}}],
        [{"user": {"login": "bob"}}, {"user": {"login": "bob"}}],
    )
    assert rows[0]["user"] == "bob"
    assert rows[0]["total"] == 3


def test_render_team_join_message_uses_team_template():
    message = worker.render_team_join_message(
        {"user": {"id": "U123", "name": "newperson"}},
        "T04T40NHX",
    )
    assert message == "welcome newperson"


class _Env:
    pass


def test_blt_app_url_response_returns_url_when_set():
    env = _Env()
    setattr(env, "SLACK_APP_URL", "https://api.slack.com/apps/A12345/general")
    response = worker.blt_app_url_response(env)
    assert response["text"] == "https://api.slack.com/apps/A12345/general"


def test_blt_app_url_response_returns_error_when_missing():
    env = _Env()
    response = worker.blt_app_url_response(env)
    assert response["text"] == "Missing required environment variable: SLACK_APP_URL"


def test_current_config_message_formats_public_values():
    env = _Env()
    setattr(env, "GITHUB_ACTIVITY_OWNER", "OWASP-BLT")
    setattr(env, "GITHUB_ACTIVITY_REPO", "BLT-Lettuce")
    setattr(env, "GITHUB_ISSUE_OWNER", "OWASP-BLT")
    setattr(env, "GITHUB_ISSUE_REPO", "BLT-Sammich")
    setattr(
        env, "SLACK_REDIRECT_URL", "https://sammich.owaspblt.org/oauth/slack/callback"
    )
    setattr(env, "SLACK_APP_URL", "https://api.slack.com/apps/A12345/general")

    message = worker.current_config_message(env, "T123", "U123")
    assert "team_id: T123" in message
    assert "installer_user_id: U123" in message
    assert "github_activity_repo: OWASP-BLT/BLT-Lettuce" in message
    assert "slack_app_url: https://api.slack.com/apps/A12345/general" in message


def test_build_slack_install_url_uses_required_env_vars():
    env = _Env()
    setattr(env, "SLACK_CLIENT_ID", "123.456")
    setattr(env, "SLACK_REDIRECT_URL", "https://example.com/oauth/slack/callback")
    setattr(env, "SLACK_OAUTH_STATE", "state-token")
    setattr(env, "SLACK_OAUTH_SCOPES", "commands,chat:write")
    setattr(env, "SLACK_OAUTH_USER_SCOPES", "users:read")

    install_url = worker.build_slack_install_url(env)
    assert install_url.startswith("https://slack.com/oauth/v2/authorize?")
    assert "client_id=123.456" in install_url
    assert (
        "redirect_uri=https%3A%2F%2Fexample.com%2Foauth%2Fslack%2Fcallback"
        in install_url
    )
    assert "state=state-token" in install_url
    assert "scope=commands%2Cchat%3Awrite" in install_url
    assert "user_scope=users%3Aread" in install_url


class _Headers:
    def __init__(self, values):
        self.values = values

    def get(self, name, default=""):
        return self.values.get(name.lower(), default)


class _Request:
    def __init__(self, authorization):
        self.headers = _Headers({"authorization": authorization})


def test_admin_path_uses_default_and_normalizes_env_value():
    env = _Env()
    assert worker.admin_path(env) == ""
    setattr(env, "ADMIN_URL", "private-admin")
    assert worker.admin_path(env) == "/private-admin"


def test_basic_auth_accepts_configured_admin_user():
    env = _Env()
    setattr(env, "ADMIN_USERNAME", "manager")
    setattr(env, "ADMIN_PASSWORD", "secret")
    token = base64.b64encode(b"manager:secret").decode("ascii")

    assert worker.is_admin_request(_Request("Basic " + token), env)


def test_basic_auth_rejects_bad_password():
    env = _Env()
    setattr(env, "ADMIN_USERNAME", "manager")
    setattr(env, "ADMIN_PASSWORD", "secret")
    token = base64.b64encode(b"manager:nope").decode("ascii")

    assert not worker.is_admin_request(_Request("Basic " + token), env)


def test_basic_auth_rejects_missing_config():
    token = base64.b64encode(b"admin:admin").decode("ascii")
    assert not worker.is_admin_request(_Request("Basic " + token), _Env())


def test_render_admin_html_includes_workspaces_and_servers():
    env = _Env()
    setattr(env, "ADMIN_URL", "/private-admin")
    html = worker.render_admin_html(
        env,
        [
            {
                "team_name": "Security Team",
                "team_id": "T123",
                "status": "connected",
                "total_activities": 7,
                "channel_count": 3,
                "member_count": 42,
            }
        ],
        [
            {
                "id": 1,
                "name": "Production",
                "url": "https://example.com",
                "status": "online",
                "description": "Main endpoint",
            }
        ],
    )

    assert "Security Team" in html
    assert "Production" in html
    assert "/private-admin" in html


def test_lettuce_model_tables_are_in_schema_bootstrap():
    migrations_dir = Path(__file__).resolve().parents[1] / "migrations"
    schema_sql = "\n".join(
        path.read_text() for path in sorted(migrations_dir.glob("*.sql"))
    )

    for table_name in (
        "slack_activity",
        "workspace_installations",
        "connected_workspaces",
        "managed_servers",
        "workspaces",
        "channels",
        "repositories",
        "github_organizations",
        "events",
        "join_messages",
        "users",
        "sessions",
        "user_workspaces",
    ):
        assert "CREATE TABLE IF NOT EXISTS {0}".format(table_name) in schema_sql


def test_public_event_rows_hide_request_payload():
    public_events = worker.build_public_events(
        [
            {
                "id": 1,
                "event_type": "Team_Join",
                "status": "success",
                "verified": 1,
                "created_at": "2026-06-06T00:00:00+00:00",
                "request_data": "secret payload",
            }
        ]
    )

    assert public_events == [
        {
            "id": 1,
            "event_type": "Team_Join",
            "status": "success",
            "verified": 1,
            "created_at": "2026-06-06T00:00:00+00:00",
        }
    ]


def test_slack_message_event_metadata_is_extracted_for_logging():
    payload = {
        "type": "event_callback",
        "event_id": "Ev123",
        "event": {
            "type": "message",
            "team": "T123",
            "user": "U123",
            "channel": "C123",
            "text": "hello from a post",
        },
        "authorizations": [{"team_id": "T123"}],
    }

    assert worker.payload_team_id(payload) == "T123"
    assert worker.payload_user_id(payload) == "U123"
    assert worker.payload_channel_id(payload) == "C123"
    assert worker.model_event_type_for_activity("event", payload) == "Message"


def test_slack_bot_message_event_metadata_is_extracted_for_logging():
    payload = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "subtype": "bot_message",
            "team": "T999",
            "bot_id": "B123",
            "channel": "C999",
        },
    }

    assert worker.payload_team_id(payload) == "T999"
    assert worker.payload_user_id(payload) == "B123"
    assert worker.payload_channel_id(payload) == "C999"
    assert worker.model_event_type_for_activity("event", payload) == "Message"


def test_db_insert_event_persists_slack_team_id_even_without_workspace():
    captured = {}
    original_d1_run = worker.d1_run
    original_schema_ready = worker.SCHEMA_READY

    async def fake_d1_run(env, query, params=None):
        captured["query"] = query
        captured["params"] = params
        return {"success": True}

    env = _Env()
    setattr(env, "DB", object())
    worker.d1_run = fake_d1_run
    worker.SCHEMA_READY = False
    try:
        asyncio.run(
            worker.db_insert_event(
                env,
                None,
                "Message",
                user_slack_id="U123",
                channel_id="C123",
                slack_team_id="T123",
                request_data='{"event": {"type": "message"}}',
            )
        )
    finally:
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    assert "slack_team_id" in captured["query"]
    assert captured["params"][0] is None
    assert captured["params"][5] == "T123"
