import base64
import asyncio
import json
from pathlib import Path

from src import worker


EVENT_INSERT_COLUMNS = [
    "workspace_id",
    "event_type",
    "user_slack_id",
    "channel_name",
    "channel_id",
    "slack_team_id",
    "api_app_id",
    "command",
    "command_text",
    "is_enterprise_install",
    "response_url",
    "team_domain",
    "trigger_id",
    "user_name",
    "slack_token",
    "request_data",
    "verified",
    "status",
    "created_at",
    "webhook_body_type",
    "webhook_event_id",
    "webhook_event_time",
    "webhook_event_subtype",
    "webhook_retry_num",
    "webhook_retry_reason",
    "slack_response_data",
]


def event_insert_values(params):
    return dict(zip(EVENT_INSERT_COLUMNS, params))


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


def test_app_home_view_lists_available_commands():
    view = worker.app_home_view()
    encoded = str(view)

    assert view["type"] == "home"
    assert "blocks" in view
    assert "/contrib" in encoded
    assert "/stats" in encoded
    assert "/discover [search term]" in encoded
    assert "/installed_apps" in encoded


def test_manifest_subscribes_to_app_home_opened():
    manifest = (Path(__file__).resolve().parents[1] / "manifest.yaml").read_text()

    assert "home_tab_enabled: true" in manifest
    assert "- app_home_opened" in manifest


def test_get_slack_endpoints_return_health_payloads():
    original_json_response = worker.json_response
    worker.json_response = lambda payload, status=200: {
        "payload": payload,
        "status": status,
    }
    try:
        events_response = asyncio.run(
            worker.handle_request(
                _RouteRequest("GET", "https://sammich.owaspblt.org/slack/events/"),
                _Env(),
            )
        )
        commands_response = asyncio.run(
            worker.handle_request(
                _RouteRequest("GET", "https://sammich.owaspblt.org/slack/commands"),
                _Env(),
            )
        )
    finally:
        worker.json_response = original_json_response

    assert events_response == {
        "payload": {
            "ok": True,
            "endpoint": "slack_events",
            "method": "POST required",
        },
        "status": 200,
    }
    assert commands_response == {
        "payload": {
            "ok": True,
            "endpoint": "slack_commands",
            "method": "POST required",
        },
        "status": 200,
    }


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


class _RouteRequest:
    def __init__(self, method, url, body=""):
        self.method = method
        self.url = url
        self.headers = _Headers({})
        self.body = body

    async def text(self):
        return self.body


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
    assert "slack_app_token" in html
    assert "slack_bot_token" in html


def test_render_admin_html_includes_database_admin_context():
    env = _Env()
    setattr(env, "ADMIN_URL", "/private-admin")
    html = worker.render_admin_html(
        env,
        [],
        [],
        database_context={
            "tables": ["workspaces", "events"],
            "counts": {"workspaces": 1, "events": 2},
            "selected_table": "workspaces",
            "schema": worker.ADMIN_TABLE_SCHEMAS["workspaces"],
            "rows": [
                {
                    "id": 1,
                    "team_id": "T123",
                    "team_name": "Security Team",
                    "created_at": "2026-06-06T00:00:00+00:00",
                    "updated_at": "2026-06-06T00:00:00+00:00",
                }
            ],
            "edit_row": None,
            "edit_pk": "",
        },
    )

    assert "Database Admin" in html
    assert "workspaces" in html
    assert "Security Team" in html
    assert "db_create" in html


def test_lettuce_model_tables_are_in_schema_bootstrap():
    migrations_dir = Path(__file__).resolve().parents[1] / "migrations"
    schema_sql = "\n".join(
        path.read_text() for path in sorted(migrations_dir.glob("*.sql"))
    )

    for table_name in (
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
    assert "DROP TABLE IF EXISTS slack_activity" in schema_sql
    assert "slack_activity" not in worker.ADMIN_TABLE_SCHEMAS
    assert "slack_response_data" in schema_sql
    for column_name in (
        "api_app_id",
        "command",
        "command_text",
        "is_enterprise_install",
        "response_url",
        "team_domain",
        "trigger_id",
        "user_name",
        "slack_token",
    ):
        assert column_name in schema_sql
        assert (column_name, "TEXT") in worker.ADMIN_TABLE_SCHEMAS["events"]["columns"]


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
    values = event_insert_values(captured["params"])
    assert values["workspace_id"] is None
    assert values["slack_team_id"] == "T123"


def test_db_insert_event_persists_slack_response_data():
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
                "Slack_API_Response",
                slack_team_id="T123",
                request_data='{"api_method": "chat.postMessage"}',
                slack_response_data='{"ok": true}',
            )
        )
    finally:
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    assert "slack_response_data" in captured["query"]
    assert event_insert_values(captured["params"])["slack_response_data"] == '{"ok": true}'


def test_db_insert_event_persists_slash_command_fields():
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
                "Command",
                slack_team_id="T070JPE5BQQ",
                channel_id="D089QRTC0A1",
                user_slack_id="U06V72UT0J1",
                channel_name="directmessage",
                api_app_id="A0AK9DQG1DG",
                command="/contrib",
                command_text="",
                is_enterprise_install="false",
                response_url="https://hooks.slack.com/commands/example",
                team_domain="owaspblt",
                trigger_id="11296066658550.7018796181840.example",
                user_name="donnie.brown",
                slack_token="Wr0cGReWOl8adfvxyV2IuMnr",
                request_data='{"command": "/contrib"}',
            )
        )
    finally:
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    values = event_insert_values(captured["params"])
    assert "api_app_id" in captured["query"]
    assert values["api_app_id"] == "A0AK9DQG1DG"
    assert values["channel_id"] == "D089QRTC0A1"
    assert values["channel_name"] == "directmessage"
    assert values["command"] == "/contrib"
    assert values["is_enterprise_install"] == "false"
    assert values["response_url"] == "https://hooks.slack.com/commands/example"
    assert values["team_domain"] == "owaspblt"
    assert values["slack_team_id"] == "T070JPE5BQQ"
    assert values["trigger_id"] == "11296066658550.7018796181840.example"
    assert values["user_slack_id"] == "U06V72UT0J1"
    assert values["user_name"] == "donnie.brown"
    assert values["slack_token"] == "Wr0cGReWOl8adfvxyV2IuMnr"


def test_d1_run_normalizes_none_params_before_binding():
    captured = {}

    class _Statement:
        def bind(self, *params):
            captured["params"] = params
            return self

        async def run(self):
            return {"success": True}

    class _DB:
        def prepare(self, query):
            captured["query"] = query
            return _Statement()

    env = _Env()
    setattr(env, "DB", _DB())

    result = asyncio.run(worker.d1_run(env, "INSERT INTO example VALUES (?, ?)", [None, "ok"]))

    assert result == {"success": True}
    assert captured["params"] == ("", "ok")


def test_db_insert_event_retries_when_slack_team_id_column_is_missing():
    captured = []
    original_d1_run = worker.d1_run
    original_schema_ready = worker.SCHEMA_READY

    async def fake_d1_run(env, query, params=None):
        captured.append((query, params))
        if "slack_team_id" in query:
            raise RuntimeError("no such column: slack_team_id")
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
                request_data='{"team_id": "T123", "event": {"type": "message"}}',
            )
        )
    finally:
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    assert len(captured) == 2
    assert "slack_team_id" in captured[0][0]
    assert "slack_team_id" not in captured[1][0]
    assert captured[1][1][0] is None
    assert captured[1][1][1] == "Message"


def test_record_activity_logs_slack_post_event_even_without_workspace():
    captured = []
    original_d1_run = worker.d1_run
    original_schema_ready = worker.SCHEMA_READY

    async def fake_d1_run(env, query, params=None):
        captured.append((query, params))
        if "SELECT * FROM workspaces" in query:
            return {"results": []}
        return {"success": True}

    payload = {
        "type": "event_callback",
        "event_id": "EvPOST",
        "event_time": "1710000000",
        "team_id": "T123",
        "event": {
            "type": "message",
            "user": "U123",
            "channel": "C123",
            "text": "this post should be logged",
        },
    }
    env = _Env()
    setattr(env, "DB", object())
    worker.d1_run = fake_d1_run
    worker.SCHEMA_READY = False
    try:
        asyncio.run(worker.record_activity(env, "event", payload))
    finally:
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    event_inserts = [
        (query, params)
        for query, params in captured
        if "INSERT INTO events" in query
    ]
    assert len(event_inserts) == 1
    values = event_insert_values(event_inserts[0][1])
    assert values["workspace_id"] is None
    assert values["event_type"] == "Message"
    assert values["slack_team_id"] == "T123"
    assert "this post should be logged" in values["request_data"]


def test_record_activity_logs_slack_post_when_workspace_lookup_fails():
    captured = []
    original_d1_run = worker.d1_run
    original_schema_ready = worker.SCHEMA_READY

    async def fake_d1_run(env, query, params=None):
        captured.append((query, params))
        if "SELECT * FROM workspaces" in query:
            raise RuntimeError("no such table: workspaces")
        return {"success": True}

    payload = {
        "type": "event_callback",
        "team_id": "TLOOKUP",
        "event": {
            "type": "message",
            "user": "U123",
            "channel": "C123",
            "text": "log me even when lookup fails",
        },
    }
    env = _Env()
    setattr(env, "DB", object())
    worker.d1_run = fake_d1_run
    worker.SCHEMA_READY = False
    try:
        asyncio.run(worker.record_activity(env, "event", payload))
    finally:
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    event_inserts = [
        (query, params)
        for query, params in captured
        if "INSERT INTO events" in query
    ]
    assert len(event_inserts) == 1
    values = event_insert_values(event_inserts[0][1])
    assert values["workspace_id"] is None
    assert values["event_type"] == "Message"
    assert values["slack_team_id"] == "TLOOKUP"


def test_record_activity_logs_slash_command_fields():
    captured = []
    original_d1_run = worker.d1_run
    original_schema_ready = worker.SCHEMA_READY

    async def fake_d1_run(env, query, params=None):
        captured.append((query, params))
        if "SELECT * FROM workspaces" in query:
            return {"results": []}
        return {"success": True}

    payload = {
        "api_app_id": "A0AK9DQG1DG",
        "channel_id": "D089QRTC0A1",
        "channel_name": "directmessage",
        "command": "/contrib",
        "is_enterprise_install": "false",
        "response_url": "https://hooks.slack.com/commands/example",
        "team_domain": "owaspblt",
        "team_id": "T070JPE5BQQ",
        "text": "",
        "token": "Wr0cGReWOl8adfvxyV2IuMnr",
        "trigger_id": "11296066658550.7018796181840.example",
        "user_id": "U06V72UT0J1",
        "user_name": "donnie.brown",
    }
    env = _Env()
    setattr(env, "DB", object())
    worker.d1_run = fake_d1_run
    worker.SCHEMA_READY = False
    try:
        asyncio.run(worker.record_activity(env, "slash_command", payload))
    finally:
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    event_inserts = [
        (query, params)
        for query, params in captured
        if "INSERT INTO events" in query
    ]
    assert len(event_inserts) == 1
    values = event_insert_values(event_inserts[0][1])
    assert values["event_type"] == "Command"
    assert values["api_app_id"] == "A0AK9DQG1DG"
    assert values["channel_id"] == "D089QRTC0A1"
    assert values["channel_name"] == "directmessage"
    assert values["command"] == "/contrib"
    assert values["is_enterprise_install"] == "false"
    assert values["response_url"] == "https://hooks.slack.com/commands/example"
    assert values["team_domain"] == "owaspblt"
    assert values["slack_team_id"] == "T070JPE5BQQ"
    assert values["trigger_id"] == "11296066658550.7018796181840.example"
    assert values["user_slack_id"] == "U06V72UT0J1"
    assert values["user_name"] == "donnie.brown"
    assert values["slack_token"] == "Wr0cGReWOl8adfvxyV2IuMnr"
    assert '"command": "/contrib"' in values["request_data"]


def test_db_upsert_workspace_persists_slack_tokens():
    captured = {}
    original_d1_run = worker.d1_run
    original_schema_ready = worker.SCHEMA_READY

    async def fake_d1_run(env, query, params=None):
        if "INSERT INTO workspaces" in query:
            captured["query"] = query
            captured["params"] = params
            return {"success": True}
        if "SELECT * FROM workspaces" in query:
            return {"results": [{"id": 9}]}
        return {"success": True}

    env = _Env()
    setattr(env, "DB", object())
    worker.d1_run = fake_d1_run
    worker.SCHEMA_READY = False
    try:
        workspace_id = asyncio.run(
            worker.db_upsert_workspace(
                env,
                team_id="T123",
                team_name="Security Team",
                app_token="xapp-token",
                bot_token="xoxb-token",
            )
        )
    finally:
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    assert workspace_id == 9
    assert "app_token" in captured["query"]
    assert "bot_token" in captured["query"]
    assert captured["params"][3] == "xapp-token"
    assert captured["params"][4] == "xoxb-token"


def test_db_admin_create_update_delete_use_whitelisted_table_schema():
    captured = []
    original_d1_run = worker.d1_run
    original_schema_ready = worker.SCHEMA_READY

    async def fake_d1_run(env, query, params=None):
        captured.append((query, params))
        return {"success": True}

    env = _Env()
    setattr(env, "DB", object())
    worker.d1_run = fake_d1_run
    worker.SCHEMA_READY = False
    try:
        asyncio.run(
            worker.db_admin_create_row(
                env,
                "managed_servers",
                {
                    "field__name": "Production",
                    "field__url": "https://example.com",
                    "field__status": "online",
                    "field__description": "Main endpoint",
                    "field__created_at": "2026-06-06T00:00:00+00:00",
                    "field__updated_at": "2026-06-06T00:00:00+00:00",
                },
            )
        )
        asyncio.run(
            worker.db_admin_update_row(
                env,
                "managed_servers",
                "7",
                {
                    "field__name": "Production 2",
                    "field__url": "https://example.com",
                    "field__status": "degraded",
                    "field__description": "Updated",
                    "field__created_at": "2026-06-06T00:00:00+00:00",
                    "field__updated_at": "2026-06-06T01:00:00+00:00",
                },
            )
        )
        asyncio.run(worker.db_admin_delete_row(env, "managed_servers", "7"))
    finally:
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    assert captured[0][0].startswith("INSERT INTO managed_servers")
    assert "id" not in captured[0][0].split("(", 1)[1].split(")", 1)[0]
    assert captured[0][1][0] == "Production"
    assert captured[1][0].startswith("UPDATE managed_servers SET")
    assert captured[1][1][-1] == "7"
    assert captured[2] == ("DELETE FROM managed_servers WHERE id = ?", ["7"])


def test_db_admin_rejects_unknown_table_names():
    try:
        worker.require_admin_table_name("managed_servers; DROP TABLE users")
    except ValueError as error:
        assert "Unknown database table" in str(error)
    else:
        raise AssertionError("unknown table name was accepted")


def test_direct_bot_message_detection_handles_im_channel():
    assert worker.is_direct_bot_message({"channel_type": "im", "channel": "C123"})
    assert worker.is_direct_bot_message({"channel": "D123"})
    assert not worker.is_direct_bot_message({"channel_type": "channel", "channel": "C123"})
    assert worker.message_mentions_bot({"text": "<@U999> hello"}, "U999")
    assert not worker.message_mentions_bot({"text": "hello"}, "U999")


def test_handle_event_payload_replies_to_direct_message():
    sent = {}
    original_post_message = worker.slack_api_post_message
    original_json_response = worker.json_response

    async def fake_post_message(channel_id, text, env, team_id=""):
        sent["channel_id"] = channel_id
        sent["text"] = text
        sent["team_id"] = team_id

    worker.slack_api_post_message = fake_post_message
    worker.json_response = lambda payload, status=200, headers=None: payload
    try:
        asyncio.run(
            worker.handle_event_payload(
                {
                    "type": "event_callback",
                    "team_id": "T123",
                    "event": {
                        "type": "message",
                        "channel_type": "im",
                        "channel": "D123",
                        "user": "U123",
                        "text": "hello",
                    },
                },
                _Env(),
            )
        )
    finally:
        worker.slack_api_post_message = original_post_message
        worker.json_response = original_json_response

    assert sent["channel_id"] == "D123"
    assert sent["team_id"] == "T123"
    assert "/stats" in sent["text"]


def test_handle_event_payload_replies_to_direct_message_when_db_lookups_fail():
    sent = {}
    original_post_message = worker.slack_api_post_message
    original_bot_user_id = worker.db_get_workspace_bot_user_id
    original_installer = worker.get_workspace_installer
    original_json_response = worker.json_response

    async def fake_post_message(channel_id, text, env, team_id=""):
        sent["channel_id"] = channel_id
        sent["text"] = text
        sent["team_id"] = team_id

    async def failing_bot_user_id(env, team_id="", channel_id=""):
        raise RuntimeError("D1 unavailable")

    async def failing_installer(env, team_id):
        raise RuntimeError("D1 unavailable")

    worker.slack_api_post_message = fake_post_message
    worker.db_get_workspace_bot_user_id = failing_bot_user_id
    worker.get_workspace_installer = failing_installer
    worker.json_response = lambda payload, status=200, headers=None: payload
    try:
        asyncio.run(
            worker.handle_event_payload(
                {
                    "type": "event_callback",
                    "team_id": "T123",
                    "event": {
                        "type": "message",
                        "channel_type": "im",
                        "channel": "D123",
                        "user": "U123",
                        "text": "help",
                    },
                },
                _Env(),
            )
        )
    finally:
        worker.slack_api_post_message = original_post_message
        worker.db_get_workspace_bot_user_id = original_bot_user_id
        worker.get_workspace_installer = original_installer
        worker.json_response = original_json_response

    assert sent["channel_id"] == "D123"
    assert sent["team_id"] == "T123"
    assert "/stats" in sent["text"]


def test_handle_event_payload_publishes_app_home_commands():
    published = {}
    original_publish_home = worker.slack_api_publish_home
    original_json_response = worker.json_response

    async def fake_publish_home(user_id, env, team_id=""):
        published["user_id"] = user_id
        published["team_id"] = team_id

    worker.slack_api_publish_home = fake_publish_home
    worker.json_response = lambda payload, status=200, headers=None: payload
    try:
        asyncio.run(
            worker.handle_event_payload(
                {
                    "type": "event_callback",
                    "team_id": "T123",
                    "event": {
                        "type": "app_home_opened",
                        "user": "U123",
                    },
                },
                _Env(),
            )
        )
    finally:
        worker.slack_api_publish_home = original_publish_home
        worker.json_response = original_json_response

    assert published == {"user_id": "U123", "team_id": "T123"}


def test_slack_api_publish_home_uses_views_publish_shape():
    captured = {}
    original_fetch_json = worker.fetch_json
    original_log_response = worker.log_slack_api_response
    original_bot_token = worker.db_get_workspace_bot_token

    async def fake_fetch_json(url, method="GET", headers=None, body=None):
        captured["url"] = url
        captured["method"] = method
        captured["headers"] = headers
        captured["body"] = json.loads(body or "{}")
        return True, {"ok": True}, 200

    async def fake_log_response(*args, **kwargs):
        captured["logged"] = True

    async def fake_bot_token(env, team_id="", channel_id=""):
        return "xoxb-token"

    worker.fetch_json = fake_fetch_json
    worker.log_slack_api_response = fake_log_response
    worker.db_get_workspace_bot_token = fake_bot_token
    try:
        asyncio.run(worker.slack_api_publish_home("U123", _Env(), team_id="T123"))
    finally:
        worker.fetch_json = original_fetch_json
        worker.log_slack_api_response = original_log_response
        worker.db_get_workspace_bot_token = original_bot_token

    assert captured["url"] == "https://slack.com/api/views.publish"
    assert captured["method"] == "POST"
    assert captured["headers"]["Authorization"] == "Bearer xoxb-token"
    assert captured["body"]["user_id"] == "U123"
    assert captured["body"]["view"]["type"] == "home"
    assert "/stats" in str(captured["body"]["view"])
    assert captured["logged"] is True


def test_slack_api_post_message_logs_slack_response_payload():
    captured = {}
    original_fetch_json = worker.fetch_json
    original_log_response = worker.log_slack_api_response
    original_bot_token = worker.db_get_workspace_bot_token

    async def fake_fetch_json(url, method="GET", headers=None, body=None):
        captured["url"] = url
        captured["body"] = body
        return True, {"ok": True, "ts": "123.456"}, 200

    async def fake_log_response(
        env,
        team_id,
        channel_id,
        user_id,
        api_method,
        request_payload,
        response_payload,
        ok,
        status_code,
    ):
        captured["log"] = {
            "team_id": team_id,
            "channel_id": channel_id,
            "api_method": api_method,
            "request_payload": request_payload,
            "response_payload": response_payload,
            "ok": ok,
            "status_code": status_code,
        }

    async def fake_bot_token(env, team_id="", channel_id=""):
        return "xoxb-token"

    worker.fetch_json = fake_fetch_json
    worker.log_slack_api_response = fake_log_response
    worker.db_get_workspace_bot_token = fake_bot_token
    try:
        asyncio.run(
            worker.slack_api_post_message(
                "C123",
                "hello",
                _Env(),
                team_id="T123",
            )
        )
    finally:
        worker.fetch_json = original_fetch_json
        worker.log_slack_api_response = original_log_response
        worker.db_get_workspace_bot_token = original_bot_token

    assert captured["url"] == "https://slack.com/api/chat.postMessage"
    assert captured["log"]["team_id"] == "T123"
    assert captured["log"]["channel_id"] == "C123"
    assert captured["log"]["api_method"] == "chat.postMessage"
    assert captured["log"]["response_payload"] == {"ok": True, "ts": "123.456"}
    assert captured["log"]["ok"] is True


def test_slack_api_post_message_falls_back_to_env_token_when_db_lookup_fails():
    captured = {}
    original_fetch_json = worker.fetch_json
    original_log_response = worker.log_slack_api_response
    original_bot_token = worker.db_get_workspace_bot_token

    async def fake_fetch_json(url, method="GET", headers=None, body=None):
        captured["authorization"] = headers.get("Authorization", "")
        captured["body"] = json.loads(body or "{}")
        return True, {"ok": True}, 200

    async def fake_log_response(*args, **kwargs):
        return None

    async def failing_bot_token(env, team_id="", channel_id=""):
        raise RuntimeError("D1 unavailable")

    env = _Env()
    setattr(env, "SLACK_BOT_TOKEN", "xoxb-env-token")
    worker.fetch_json = fake_fetch_json
    worker.log_slack_api_response = fake_log_response
    worker.db_get_workspace_bot_token = failing_bot_token
    try:
        asyncio.run(worker.slack_api_post_message("D123", "hello", env, team_id="T123"))
    finally:
        worker.fetch_json = original_fetch_json
        worker.log_slack_api_response = original_log_response
        worker.db_get_workspace_bot_token = original_bot_token

    assert captured["authorization"] == "Bearer xoxb-env-token"
    assert captured["body"] == {"channel": "D123", "text": "hello"}


def test_handle_event_payload_replies_when_bot_is_mentioned_in_channel_message():
    sent = {}
    original_post_message = worker.slack_api_post_message
    original_bot_user_id = worker.db_get_workspace_bot_user_id
    original_json_response = worker.json_response

    async def fake_post_message(channel_id, text, env, team_id=""):
        sent["channel_id"] = channel_id
        sent["text"] = text
        sent["team_id"] = team_id

    async def fake_bot_user_id(env, team_id="", channel_id=""):
        return "U999"

    worker.slack_api_post_message = fake_post_message
    worker.db_get_workspace_bot_user_id = fake_bot_user_id
    worker.json_response = lambda payload, status=200, headers=None: payload
    try:
        asyncio.run(
            worker.handle_event_payload(
                {
                    "type": "event_callback",
                    "team_id": "T123",
                    "event": {
                        "type": "message",
                        "channel_type": "channel",
                        "channel": "C123",
                        "user": "U123",
                        "text": "<@U999> hello",
                    },
                },
                _Env(),
            )
        )
    finally:
        worker.slack_api_post_message = original_post_message
        worker.db_get_workspace_bot_user_id = original_bot_user_id
        worker.json_response = original_json_response

    assert sent["channel_id"] == "C123"
    assert sent["team_id"] == "T123"
    assert "/stats" in sent["text"]


def test_handle_event_payload_does_not_reply_to_bot_self_message():
    sent = {}
    original_post_message = worker.slack_api_post_message
    original_bot_user_id = worker.db_get_workspace_bot_user_id
    original_json_response = worker.json_response

    async def fake_post_message(channel_id, text, env, team_id=""):
        sent["channel_id"] = channel_id

    async def fake_bot_user_id(env, team_id="", channel_id=""):
        return "U999"

    worker.slack_api_post_message = fake_post_message
    worker.db_get_workspace_bot_user_id = fake_bot_user_id
    worker.json_response = lambda payload, status=200, headers=None: payload
    try:
        asyncio.run(
            worker.handle_event_payload(
                {
                    "type": "event_callback",
                    "team_id": "T123",
                    "event": {
                        "type": "message",
                        "channel_type": "im",
                        "channel": "D123",
                        "user": "U999",
                        "text": "hello",
                    },
                },
                _Env(),
            )
        )
    finally:
        worker.slack_api_post_message = original_post_message
        worker.db_get_workspace_bot_user_id = original_bot_user_id
        worker.json_response = original_json_response

    assert sent == {}
