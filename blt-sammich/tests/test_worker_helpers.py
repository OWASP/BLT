import base64
import asyncio
import contextlib
import io
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
    "internal_error",
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
    view = worker.app_home_view(
        user_id="U123",
        team_name="OWASP",
        base_url="https://sammich.example",
        version="9.8.7",
    )
    encoded = str(view)

    assert view["type"] == "home"
    assert "blocks" in view
    assert "Welcome to BLT Sammich, <@U123>" in encoded
    assert "OWASP" in encoded
    assert "Open Dashboard" in encoded
    assert "https://sammich.example" in encoded
    assert "Running version `9.8.7`" in encoded
    assert "/contrib" in encoded
    assert "/stats" in encoded
    assert "/discover [search term]" in encoded
    assert "/blt-welcome" in encoded
    assert "/installed_apps" in encoded


def test_manifest_subscribes_to_app_home_opened():
    manifest = (Path(__file__).resolve().parents[1] / "manifest.yaml").read_text()

    assert "home_tab_enabled: true" in manifest
    assert "- app_home_opened" in manifest


def test_get_slack_endpoints_return_health_payloads():
    original_json_response = worker.json_response
    original_record_activity = worker.record_activity
    logged = []

    async def fake_record_activity(env, activity_kind, payload):
        logged.append((activity_kind, payload))

    worker.json_response = lambda payload, status=200: {
        "payload": payload,
        "status": status,
    }
    worker.record_activity = fake_record_activity
    try:
        events_response = asyncio.run(
            worker.handle_request(
                _RouteRequest(
                    "GET",
                    "https://sammich.owaspblt.org/slack/events/",
                    headers={
                        "user-agent": "Chrome test",
                        "cf-ray": "a0788b78edb67cae",
                    },
                ),
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
        worker.record_activity = original_record_activity
        worker.json_response = original_json_response

    assert logged == []
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


def test_post_slack_events_logs_event_before_signature_verification():
    original_record_activity = worker.record_activity
    original_build_response = worker.build_response
    logged = []

    async def fake_record_activity(env, activity_kind, payload):
        logged.append((activity_kind, payload))

    worker.record_activity = fake_record_activity
    worker.build_response = lambda body, status=200, content_type="text/plain; charset=utf-8", headers=None: {
        "body": body,
        "status": status,
    }
    try:
        response = asyncio.run(
            worker.handle_request(
                _RouteRequest(
                    "POST",
                    "https://sammich.owaspblt.org/slack/events",
                    body=json.dumps(
                        {
                            "type": "event_callback",
                            "team_id": "T123",
                            "event": {
                                "type": "message",
                                "channel": "C123",
                                "user": "U123",
                                "text": "log before auth",
                            },
                        }
                    ),
                    headers={
                        "content-type": "application/json",
                        "user-agent": "Slackbot test",
                    },
                ),
                _Env(),
            )
        )
    finally:
        worker.build_response = original_build_response
        worker.record_activity = original_record_activity

    assert response == {"body": "Invalid Slack signature.", "status": 401}
    assert len(logged) == 1
    assert logged[0][0] == "event"
    assert logged[0][1]["team_id"] == "T123"
    assert logged[0][1]["event"]["text"] == "log before auth"


def test_post_slack_events_can_verify_with_database_signing_secret():
    import hashlib
    import hmac

    original_record_activity = worker.record_activity
    original_handle_event_payload = worker.handle_event_payload
    original_json_response = worker.json_response
    original_signing_secret = worker.db_get_slack_app_signing_secret
    body = json.dumps(
        {
            "type": "event_callback",
            "api_app_id": "A123",
            "team_id": "T123",
            "event": {
                "type": "message",
                "channel": "C123",
                "user": "U123",
                "text": "verified by db secret",
            },
        }
    )
    timestamp = str(int(worker.time.time()))
    db_secret = "db-signing-secret"
    signature = "v0=" + hmac.new(
        db_secret.encode("utf-8"),
        "v0:{0}:{1}".format(timestamp, body).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    logged = []
    handled = {}

    async def fake_record_activity(env, activity_kind, payload):
        logged.append((activity_kind, payload))

    async def fake_handle_event_payload(payload, env):
        handled["payload"] = payload
        return {"ok": True, "handled": True}

    async def fake_signing_secret(env, app_id=""):
        handled["app_id"] = app_id
        return db_secret

    env = _Env()
    setattr(env, "SLACK_SIGNING_SECRET", "wrong-env-secret")
    worker.record_activity = fake_record_activity
    worker.handle_event_payload = fake_handle_event_payload
    worker.db_get_slack_app_signing_secret = fake_signing_secret
    worker.json_response = lambda payload, status=200: payload
    try:
        response = asyncio.run(
            worker.handle_request(
                _RouteRequest(
                    "POST",
                    "https://sammich.owaspblt.org/slack/events",
                    body=body,
                    headers={
                        "content-type": "application/json",
                        "x-slack-request-timestamp": timestamp,
                        "x-slack-signature": signature,
                    },
                ),
                env,
            )
        )
    finally:
        worker.json_response = original_json_response
        worker.db_get_slack_app_signing_secret = original_signing_secret
        worker.handle_event_payload = original_handle_event_payload
        worker.record_activity = original_record_activity

    assert response == {"ok": True, "handled": True}
    assert handled["app_id"] == "A123"
    assert handled["payload"]["event"]["text"] == "verified by db secret"
    assert [entry[0] for entry in logged] == ["event"]


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
    assert "Welcome to the OWASP Slack Community, <@U123>!" in message
    assert "#introductions" in message
    assert "#contribute" in message
    assert "#project-blt" in message


def test_workspace_welcome_message_links_known_channels():
    message = worker.link_workspace_channel_names(
        worker.render_team_join_message({"user": {"id": "U123"}}, "T070JPE5BQQ"),
        [
            {"channel_id": "C077QBBLY1Z", "channel_name": "contribute"},
            {"channel_id": "CNEWS", "channel_name": "newsroom"},
        ],
    )

    assert "<@U123>" in message
    assert "<#C077QBBLY1Z|contribute>" in message
    assert "<#CNEWS|newsroom>" in message


def test_channel_join_message_template_renders_user_and_channel_context():
    template = worker.get_channel_join_message("T070JPE5BQQ", "C077QBBLY1Z")
    rendered = worker.render_join_message_template(
        template,
        {
            "user_id": "U123",
            "channel_name": "contribute",
            "channel_id": "C077QBBLY1Z",
        },
    )

    assert "Welcome <@U123> to *#contribute*!" in rendered
    assert "good first issue" in rendered


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

    def items(self):
        return self.values.items()


class _Request:
    def __init__(self, authorization):
        self.headers = _Headers({"authorization": authorization})


class _RouteRequest:
    def __init__(self, method, url, body="", headers=None):
        self.method = method
        self.url = url
        self.headers = _Headers(headers or {})
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


def test_render_admin_html_focuses_on_database_admin():
    env = _Env()
    setattr(env, "ADMIN_URL", "/private-admin")
    html = worker.render_admin_html(
        env,
        [],
        [],
        database_context={
            "tables": ["teams"],
            "counts": {"teams": 1},
            "selected_table": "teams",
            "schema": worker.ADMIN_TABLE_SCHEMAS["teams"],
            "rows": [{"id": 1, "team_id": "T123", "team_name": "Security Team"}],
            "edit_row": None,
            "edit_pk": "",
            "add_row": False,
            "sort_column": "id",
            "sort_direction": "DESC",
        },
    )

    assert "Database Admin" in html
    assert "Security Team" in html
    assert "<th" in html
    assert "href=\"/private-admin?table=teams&sort=team_id&direction=asc\"" in html
    assert "/private-admin" in html
    assert "Connected Workspaces" not in html
    assert "Managed Servers" not in html
    assert "Add Workspace" not in html
    assert "Add Server" not in html


def test_render_admin_html_includes_database_admin_context():
    env = _Env()
    setattr(env, "ADMIN_URL", "/private-admin")
    html = worker.render_admin_html(
        env,
        [],
        [],
        database_context={
            "tables": ["teams", "events"],
            "counts": {"teams": 1, "events": 2},
            "selected_table": "teams",
            "schema": worker.ADMIN_TABLE_SCHEMAS["teams"],
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
            "add_row": False,
            "sort_column": "team_name",
            "sort_direction": "ASC",
        },
    )

    assert "Database Admin" in html
    assert "Tables" in html
    assert "Admin" in html
    assert "Rows" in html
    assert "teams" in html
    assert "Security Team" in html
    assert "team_name ▲" in html
    assert "Edit" in html
    assert "Delete" in html
    assert "Refresh channels" in html
    assert "refresh_workspace_channels" in html


def test_render_admin_channel_refresh_button_only_for_teams():
    env = _Env()
    setattr(env, "ADMIN_URL", "/private-admin")
    html = worker.render_admin_row_table(
        {
            "selected_table": "channels",
            "schema": worker.ADMIN_TABLE_SCHEMAS["channels"],
            "rows": [{"id": 1, "workspace_id": 1, "channel_id": "C123"}],
            "sort_column": "id",
            "sort_direction": "DESC",
        },
        "/private-admin",
    )

    assert "Refresh channels" not in html
    assert "refresh_workspace_channels" not in html


def test_render_admin_row_table_includes_bulk_delete_controls():
    html = worker.render_admin_row_table(
        {
            "selected_table": "channels",
            "schema": worker.ADMIN_TABLE_SCHEMAS["channels"],
            "rows": [
                {"id": 1, "workspace_id": 1, "channel_id": "C123"},
                {"id": 2, "workspace_id": 1, "channel_id": "C456"},
            ],
            "sort_column": "id",
            "sort_direction": "DESC",
        },
        "/private-admin",
    )

    assert 'name="action" value="db_bulk_delete"' in html
    assert 'name="table" value="channels"' in html
    assert "Delete selected" in html
    assert 'name="row_pk__0" value="1"' in html
    assert 'name="row_pk__1" value="2"' in html
    assert 'form="admin-bulk-delete-form"' in html


def test_render_admin_row_table_collapses_payload_columns_to_one_line():
    html = worker.render_admin_row_table(
        {
            "selected_table": "events",
            "schema": worker.ADMIN_TABLE_SCHEMAS["events"],
            "rows": [
                {
                    "id": 1,
                    "request_data": '{\n  "command": "/blt",\n  "text": "help"\n}',
                    "slack_response_data": '{\n  "ok": true\n}',
                }
            ],
            "sort_column": "id",
            "sort_direction": "DESC",
        },
        "/private-admin",
    )

    assert '{ "command": "/blt", "text": "help" }' in html
    assert '{ "ok": true }' in html
    assert 'title="{ &quot;command&quot;: &quot;/blt&quot;, &quot;text&quot;: &quot;help&quot; }"' in html
    assert "whitespace-pre-wrap" not in html
    assert "break-words" not in html


def test_admin_bulk_delete_pk_values_dedupes_selected_rows():
    assert worker.admin_bulk_delete_pk_values(
        {
            "row_pk__0": "1",
            "row_pk__1": "2",
            "row_pk__2": "1",
            "row_pk__3": "",
            "table": "channels",
        }
    ) == ["1", "2"]


def test_render_admin_html_shows_edit_form_on_edit_page():
    env = _Env()
    setattr(env, "ADMIN_URL", "/private-admin")
    html = worker.render_admin_html(
        env,
        [],
        [],
        database_context={
            "tables": ["teams"],
            "counts": {"teams": 1},
            "selected_table": "teams",
            "schema": worker.ADMIN_TABLE_SCHEMAS["teams"],
            "rows": [],
            "edit_row": {
                "id": 1,
                "team_id": "T123",
                "team_name": "Security Team",
                "created_at": "2026-06-06T00:00:00+00:00",
                "updated_at": "2026-06-06T00:00:00+00:00",
            },
            "edit_pk": "1",
            "add_row": False,
            "sort_column": "id",
            "sort_direction": "DESC",
        },
    )

    assert "Edit teams" in html
    assert "db_update" in html
    assert "Delete Row" in html
    assert "Back to table" in html


def test_lettuce_model_tables_are_in_schema_bootstrap():
    migrations_dir = Path(__file__).resolve().parents[1] / "migrations"
    schema_sql = "\n".join(
        path.read_text() for path in sorted(migrations_dir.glob("*.sql"))
    )

    for table_name in (
        "slack_apps",
        "channels",
        "repositories",
        "github_organizations",
        "events",
        "users",
    ):
        assert "CREATE TABLE IF NOT EXISTS {0}".format(table_name) in schema_sql
    assert "CREATE TABLE IF NOT EXISTS workspaces" in schema_sql
    assert "ALTER TABLE workspaces RENAME TO teams" in schema_sql
    for table_name in (
        "sessions",
        "workspace_installations",
        "connected_workspaces",
        "managed_servers",
        "join_messages",
        "user_workspaces",
    ):
        assert "DROP TABLE IF EXISTS {0}".format(table_name) in schema_sql
        assert table_name not in worker.ADMIN_TABLE_SCHEMAS
    assert "DROP TABLE IF EXISTS slack_activity" in schema_sql
    assert "slack_activity" not in worker.ADMIN_TABLE_SCHEMAS
    assert "slack_response_data" in schema_sql
    assert "internal_error" in schema_sql
    assert "client_secret" in schema_sql
    assert "signing_secret" in schema_sql
    assert "bot_token" in schema_sql
    assert "bot_user_id" in schema_sql
    assert ("client_secret", "TEXT") in worker.ADMIN_TABLE_SCHEMAS["slack_apps"]["columns"]
    assert ("signing_secret", "TEXT") in worker.ADMIN_TABLE_SCHEMAS["slack_apps"]["columns"]
    assert ("bot_token", "TEXT") in worker.ADMIN_TABLE_SCHEMAS["slack_apps"]["columns"]
    assert ("bot_user_id", "TEXT") in worker.ADMIN_TABLE_SCHEMAS["slack_apps"]["columns"]
    for column_name in (
        "real_name",
        "is_bot",
        "is_admin",
        "tz",
        "profile_json",
        "metadata_json",
    ):
        assert column_name in schema_sql
        assert column_name in [name for name, _ in worker.ADMIN_TABLE_SCHEMAS["users"]["columns"]]
    for column_name in (
        "is_channel",
        "is_im",
        "is_archived",
        "creator",
        "locale",
        "metadata_json",
    ):
        assert column_name in schema_sql
        assert column_name in [name for name, _ in worker.ADMIN_TABLE_SCHEMAS["channels"]["columns"]]
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
        "internal_error",
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


def test_team_join_history_fills_last_30_days():
    history = worker.build_team_join_history(
        [
            {"day": "2026-05-09", "joins": 2},
            {"day": "2026-06-06", "joins": 5},
        ],
        today=worker.datetime(2026, 6, 6, tzinfo=worker.timezone.utc),
    )

    assert len(history) == 30
    assert history[0] == {"date": "2026-05-08", "joins": 0}
    assert history[1] == {"date": "2026-05-09", "joins": 2}
    assert history[-1] == {"date": "2026-06-06", "joins": 5}
    assert sum(day["joins"] for day in history) == 7


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


def test_slack_user_and_channel_objects_are_extracted_for_models():
    payload = {
        "type": "event_callback",
        "team_id": "T123",
        "event": {
            "type": "message",
            "user": {
                "id": "U123",
                "team_id": "T123",
                "name": "donnie",
                "real_name": "Donnie Brown",
                "is_bot": False,
                "is_admin": True,
                "tz": "America/New_York",
                "tz_label": "Eastern Daylight Time",
                "tz_offset": -14400,
                "profile": {
                    "email": "donnie@example.com",
                    "image_192": "https://example.com/avatar.png",
                },
            },
            "channel": {
                "id": "C123",
                "name": "general",
                "is_channel": True,
                "is_archived": False,
                "is_general": True,
                "num_members": 42,
                "creator": "U999",
                "topic": {"value": "Security"},
                "purpose": {"value": "Project discussion"},
            },
            "text": "hello",
        },
    }

    user = worker.payload_user_metadata(payload)
    channel = worker.payload_channel_metadata(payload)

    assert worker.payload_user_id(payload) == "U123"
    assert user["real_name"] == "Donnie Brown"
    assert user["email"] == "donnie@example.com"
    assert user["is_admin"] == 1
    assert user["tz_offset"] == -14400
    assert '"email":"donnie@example.com"' in user["profile_json"]
    assert worker.payload_channel_id(payload) == "C123"
    assert channel["channel_name"] == "general"
    assert channel["member_count"] == 42
    assert channel["is_channel"] == 1
    assert channel["is_general"] == 1
    assert channel["creator"] == "U999"
    assert channel["topic"] == "Security"
    assert '"name":"general"' in channel["metadata_json"]


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
                internal_error="diagnostic text",
            )
        )
    finally:
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    assert "slack_response_data" in captured["query"]
    assert event_insert_values(captured["params"])["slack_response_data"] == '{"ok": true}'
    assert event_insert_values(captured["params"])["internal_error"] == "diagnostic text"


def test_log_slack_api_response_adds_internal_error_for_invalid_user():
    captured = {}
    original_d1_run = worker.d1_run
    original_schema_ready = worker.SCHEMA_READY

    async def fake_d1_run(env, query, params=None):
        if "SELECT * FROM teams" in query:
            return {"results": [{"id": 15, "team_id": "T04T40NHX"}]}
        if "INSERT INTO events" in query:
            captured["query"] = query
            captured["params"] = params
            return {"success": True}
        return {"success": True}

    env = _Env()
    setattr(env, "DB", object())
    worker.d1_run = fake_d1_run
    worker.SCHEMA_READY = True
    try:
        asyncio.run(
            worker.log_slack_api_response(
                env,
                team_id="T04T40NHX",
                channel_id="",
                user_id="U04TJF11F",
                app_id="A089A036135",
                api_method="conversations.open",
                request_payload={"users": "U04TJF11F"},
                response_payload={"ok": False, "error": "user_not_found"},
                ok=False,
                status_code=200,
            )
        )
    finally:
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    values = event_insert_values(captured["params"])
    assert values["workspace_id"] == 15
    assert values["api_app_id"] == "A089A036135"
    assert values["status"] == "error"
    assert "could not find user U04TJF11F" in values["internal_error"]
    assert "A089A036135" in values["internal_error"]


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
        if "SELECT * FROM teams" in query:
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
        if "SELECT * FROM teams" in query:
            raise RuntimeError("no such table: teams")
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
        if "SELECT * FROM teams" in query:
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
    app_inserts = [
        (query, params)
        for query, params in captured
        if "INSERT INTO slack_apps" in query
    ]
    workspace_inserts = [
        (query, params)
        for query, params in captured
        if "INSERT INTO teams" in query
    ]
    assert len(app_inserts) == 1
    assert app_inserts[0][1][0] == "A0AK9DQG1DG"
    assert len(workspace_inserts) == 1
    assert workspace_inserts[0][1][6] == "A0AK9DQG1DG"
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


def test_record_activity_stores_slack_user_and_channel_metadata():
    captured = []
    original_d1_run = worker.d1_run
    original_schema_ready = worker.SCHEMA_READY

    async def fake_d1_run(env, query, params=None):
        captured.append((query, params))
        if "SELECT * FROM teams" in query:
            return {"results": [{"id": 5}]}
        if "SELECT * FROM users" in query:
            return {"results": []}
        if "SELECT id FROM slack_apps" in query:
            return {"results": [{"id": 3}]}
        return {"success": True}

    payload = {
        "type": "event_callback",
        "api_app_id": "A123",
        "team_id": "T123",
        "event": {
            "type": "message",
            "user": {
                "id": "U123",
                "team_id": "T123",
                "name": "donnie",
                "real_name": "Donnie Brown",
                "is_admin": True,
                "tz": "America/New_York",
                "profile": {
                    "email": "donnie@example.com",
                    "image_192": "https://example.com/avatar.png",
                },
            },
            "channel": {
                "id": "C123",
                "name": "general",
                "num_members": 42,
                "is_channel": True,
                "is_general": True,
                "creator": "U999",
                "topic": {"value": "Security"},
                "purpose": {"value": "Project discussion"},
            },
            "text": "hello",
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

    user_inserts = [
        (query, params)
        for query, params in captured
        if "INSERT INTO users" in query
    ]
    channel_inserts = [
        (query, params)
        for query, params in captured
        if "INSERT INTO channels" in query
    ]

    assert len(user_inserts) == 1
    assert user_inserts[0][1][0] == "U123"
    assert user_inserts[0][1][2] == "donnie"
    assert user_inserts[0][1][3] == "Donnie Brown"
    assert user_inserts[0][1][4] == "donnie@example.com"
    assert user_inserts[0][1][9] == 1
    assert '"email":"donnie@example.com"' in user_inserts[0][1][18]
    assert '"real_name":"Donnie Brown"' in user_inserts[0][1][19]

    assert len(channel_inserts) == 1
    assert channel_inserts[0][1][0] == 5
    assert channel_inserts[0][1][1] == "T123"
    assert channel_inserts[0][1][2] == "C123"
    assert channel_inserts[0][1][3] == "general"
    assert channel_inserts[0][1][4] == 42
    assert channel_inserts[0][1][5] == "Security"
    assert channel_inserts[0][1][6] == "Project discussion"
    assert channel_inserts[0][1][8] == 1
    assert channel_inserts[0][1][13] == 1
    assert channel_inserts[0][1][19] == "U999"
    assert '"name":"general"' in channel_inserts[0][1][21]


def test_record_activity_ignores_http_request_events():
    captured = []
    original_d1_run = worker.d1_run
    original_schema_ready = worker.SCHEMA_READY

    async def fake_d1_run(env, query, params=None):
        captured.append((query, params))
        return {"success": True}

    payload = {
        "type": "http_request",
        "method": "GET",
        "url": "https://sammich.owaspblt.org/slack/events",
        "path": "/slack/events",
        "headers": {
            "user-agent": "Chrome test",
            "cf-ray": "a0788b78edb67cae",
        },
        "cf": {"colo": "EWR", "country": "US"},
    }
    env = _Env()
    setattr(env, "DB", object())
    worker.d1_run = fake_d1_run
    worker.SCHEMA_READY = False
    try:
        asyncio.run(worker.record_activity(env, "http_request", payload))
        asyncio.run(worker.record_activity(env, "event", payload))
        inserted = asyncio.run(worker.db_insert_event(env, None, "Http_Request"))
    finally:
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    event_inserts = [
        (query, params)
        for query, params in captured
        if "INSERT INTO events" in query
    ]
    assert event_inserts == []
    assert inserted is False


def test_db_upsert_workspace_persists_slack_tokens():
    captured = {}
    original_d1_run = worker.d1_run
    original_schema_ready = worker.SCHEMA_READY

    async def fake_d1_run(env, query, params=None):
        if "INSERT INTO teams" in query:
            captured["query"] = query
            captured["params"] = params
            return {"success": True}
        if "SELECT * FROM teams" in query:
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
                app_id="A089A036135",
            )
        )
    finally:
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    assert workspace_id == 9
    assert "app_token" in captured["query"]
    assert "bot_token" in captured["query"]
    assert "ON CONFLICT(team_id) DO UPDATE" in captured["query"]
    assert "excluded.access_token != '' OR excluded.bot_token != ''" in captured["query"]
    assert captured["params"][3] == "xapp-token"
    assert captured["params"][4] == "xoxb-token"
    assert captured["params"][6] == "A089A036135"


def test_db_get_workspace_bot_token_prefers_matching_app_row():
    captured = {"queries": []}
    original_d1_run = worker.d1_run
    original_schema_ready = worker.SCHEMA_READY

    async def fake_d1_run(env, query, params=None):
        captured["queries"].append((query, params))
        if "WHERE team_id = ? AND app_id = ?" in query:
            return {
                "results": [
                    {
                        "id": 9,
                        "team_id": "T123",
                        "app_id": "A089A036135",
                        "bot_token": "xoxb-app-specific",
                    }
                ]
            }
        if "WHERE team_id = ?" in query:
            return {
                "results": [
                    {
                        "id": 7,
                        "team_id": "T123",
                        "app_id": "AOLD",
                        "bot_token": "xoxb-old",
                    }
                ]
            }
        return {"success": True}

    env = _Env()
    setattr(env, "DB", object())
    worker.d1_run = fake_d1_run
    worker.SCHEMA_READY = True
    try:
        token = asyncio.run(
            worker.db_get_workspace_bot_token(
                env, team_id="T123", app_id="A089A036135"
            )
        )
    finally:
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    assert token == "xoxb-app-specific"
    assert captured["queries"][0][1] == ["T123", "A089A036135"]
    assert len(captured["queries"]) == 1


def test_db_get_workspace_bot_token_falls_back_to_slack_app_row():
    captured = {"queries": []}
    original_d1_run = worker.d1_run
    original_schema_ready = worker.SCHEMA_READY

    async def fake_d1_run(env, query, params=None):
        captured["queries"].append((query, params))
        if "WHERE team_id = ? AND app_id = ?" in query:
            return {"results": []}
        if "FROM slack_apps WHERE app_id = ?" in query:
            return {
                "results": [
                    {
                        "id": 3,
                        "app_id": "A089A036135",
                        "bot_token": "xoxb-app-row",
                        "bot_user_id": "UBOT",
                    }
                ]
            }
        if "WHERE team_id = ?" in query:
            return {
                "results": [
                    {
                        "id": 7,
                        "team_id": "T123",
                        "bot_token": "xoxb-team-row",
                    }
                ]
            }
        return {"success": True}

    env = _Env()
    setattr(env, "DB", object())
    worker.d1_run = fake_d1_run
    worker.SCHEMA_READY = True
    try:
        token = asyncio.run(
            worker.db_get_workspace_bot_token(
                env, team_id="T123", app_id="A089A036135"
            )
        )
        bot_user_id = asyncio.run(
            worker.db_get_workspace_bot_user_id(
                env, team_id="T123", app_id="A089A036135"
            )
        )
    finally:
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    assert token == "xoxb-app-row"
    assert bot_user_id == "UBOT"
    assert captured["queries"][0][1] == ["T123", "A089A036135"]
    assert captured["queries"][1][1] == ["A089A036135"]


def test_db_upsert_workspace_does_not_relabel_app_id_without_token():
    captured = {}
    original_d1_run = worker.d1_run
    original_schema_ready = worker.SCHEMA_READY

    async def fake_d1_run(env, query, params=None):
        if "INSERT INTO teams" in query:
            captured["query"] = query
            captured["params"] = params
            return {"success": True}
        if "SELECT * FROM teams" in query:
            return {"results": [{"id": 9}]}
        return {"success": True}

    env = _Env()
    setattr(env, "DB", object())
    worker.d1_run = fake_d1_run
    worker.SCHEMA_READY = True
    try:
        workspace_id = asyncio.run(
            worker.db_upsert_workspace(
                env,
                team_id="T123",
                team_name="Security Team",
                app_id="A089A036135",
            )
        )
    finally:
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    assert workspace_id == 9
    assert captured["params"][2] == ""
    assert captured["params"][4] == ""
    assert captured["params"][6] == "A089A036135"
    assert "excluded.access_token != '' OR excluded.bot_token != ''" in captured["query"]


def test_refresh_workspace_channels_fetches_pages_and_persists_metadata():
    calls = {"fetch_urls": [], "channel_params": [], "count_params": None}
    original_fetch_json = worker.fetch_json
    original_d1_run = worker.d1_run
    original_schema_ready = worker.SCHEMA_READY

    async def fake_fetch_json(url, method="GET", headers=None, body=None):
        calls["fetch_urls"].append(url)
        assert headers["Authorization"] == "Bearer xoxb-workspace"
        if "cursor=page-2" in url:
            return (
                True,
                {
                    "ok": True,
                    "channels": [
                        {
                            "id": "G123",
                            "name": "private-project",
                            "is_group": True,
                            "is_private": True,
                            "num_members": 2,
                            "purpose": {"value": "Private planning"},
                        }
                    ],
                    "response_metadata": {"next_cursor": ""},
                },
                200,
            )
        return (
            True,
            {
                "ok": True,
                "channels": [
                    {
                        "id": "C123",
                        "name": "general",
                        "is_channel": True,
                        "is_general": True,
                        "num_members": 42,
                        "topic": {"value": "Security"},
                        "creator": "U999",
                    }
                ],
                "response_metadata": {"next_cursor": "page-2"},
            },
            200,
        )

    async def fake_d1_run(env, query, params=None):
        if "SELECT * FROM teams WHERE id = ?" in query:
            return {
                "results": [
                    {"id": 7, "team_id": "T123", "bot_token": "xoxb-workspace"}
                ]
            }
        if "INSERT INTO channels" in query:
            calls["channel_params"].append(params)
            return {"success": True}
        if "UPDATE teams SET channel_count" in query:
            calls["count_params"] = params
            return {"success": True}
        return {"success": True}

    env = _Env()
    setattr(env, "DB", object())
    worker.fetch_json = fake_fetch_json
    worker.d1_run = fake_d1_run
    worker.SCHEMA_READY = True
    try:
        result = asyncio.run(worker.refresh_workspace_channels_from_slack(env, 7))
    finally:
        worker.fetch_json = original_fetch_json
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    assert result == {"channel_count": 2, "member_count": 44}
    assert len(calls["fetch_urls"]) == 2
    assert calls["channel_params"][0][1] == "T123"
    assert calls["channel_params"][0][2] == "C123"
    assert calls["channel_params"][0][3] == "general"
    assert calls["channel_params"][0][4] == 42
    assert calls["channel_params"][0][5] == "Security"
    assert calls["channel_params"][0][19] == "U999"
    assert '"name":"general"' in calls["channel_params"][0][21]
    assert calls["channel_params"][1][2] == "G123"
    assert calls["channel_params"][1][7] == 1
    assert calls["count_params"][0] == 2
    assert calls["count_params"][1] == 44
    assert calls["count_params"][3] == 7


def test_refresh_workspace_channels_missing_scope_names_workspace_and_scopes():
    original_fetch_json = worker.fetch_json
    original_d1_run = worker.d1_run
    original_schema_ready = worker.SCHEMA_READY

    async def fake_fetch_json(url, method="GET", headers=None, body=None):
        return (
            True,
            {
                "ok": False,
                "error": "missing_scope",
                "needed": "channels:read,groups:read",
                "provided": "chat:write",
            },
            200,
        )

    async def fake_d1_run(env, query, params=None):
        if "SELECT * FROM teams WHERE id = ?" in query:
            return {
                "results": [
                    {
                        "id": 7,
                        "team_id": "T123",
                        "team_name": "Security Team",
                        "bot_token": "xoxb-workspace",
                    }
                ]
            }
        return {"success": True}

    env = _Env()
    setattr(env, "DB", object())
    worker.fetch_json = fake_fetch_json
    worker.d1_run = fake_d1_run
    worker.SCHEMA_READY = True
    try:
        try:
            asyncio.run(worker.refresh_workspace_channels_from_slack(env, 7))
            raised = ""
        except RuntimeError as error:
            raised = str(error)
    finally:
        worker.fetch_json = original_fetch_json
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    assert "missing_scope" in raised
    assert "workspace_id 7" in raised
    assert "team_id T123" in raised
    assert "team_name Security Team" in raised
    assert "needed scopes channels:read,groups:read" in raised
    assert "provided scopes chat:write" in raised


def test_handle_channel_join_event_sends_ephemeral_file_template():
    captured = {"logs": [], "ephemeral": None}
    original_get_workspace = worker.db_get_workspace_by_team
    original_get_name = worker.db_get_channel_name
    original_log = worker.db_log_event
    original_ephemeral = worker.slack_api_send_ephemeral

    async def fake_get_workspace(env, team_id):
        return {"id": 7, "team_id": team_id, "team_name": "OWASP"}

    async def fake_get_name(env, workspace_id, channel_id):
        return "contribute"

    async def fake_log(env, workspace_id, event_type, **kwargs):
        captured["logs"].append((workspace_id, event_type, kwargs))
        return True

    async def fake_ephemeral(
        channel_id,
        user_id,
        text,
        env,
        team_id="",
        blocks=None,
        branding_tracking_id="",
    ):
        captured["ephemeral"] = {
            "channel_id": channel_id,
            "user_id": user_id,
            "text": text,
            "team_id": team_id,
            "blocks": blocks,
            "branding_tracking_id": branding_tracking_id,
        }
        return {"ok": True, "ts": "123.456"}

    worker.db_get_workspace_by_team = fake_get_workspace
    worker.db_get_channel_name = fake_get_name
    worker.db_log_event = fake_log
    worker.slack_api_send_ephemeral = fake_ephemeral
    try:
        result = asyncio.run(
            worker.handle_channel_join_event(
                _Env(),
                {"user": "U123", "channel": "C077QBBLY1Z"},
                team_id="T070JPE5BQQ",
                source_event="member_joined_channel",
            )
        )
    finally:
        worker.db_get_workspace_by_team = original_get_workspace
        worker.db_get_channel_name = original_get_name
        worker.db_log_event = original_log
        worker.slack_api_send_ephemeral = original_ephemeral

    assert result["ok"]
    assert captured["ephemeral"]["channel_id"] == "C077QBBLY1Z"
    assert captured["ephemeral"]["user_id"] == "U123"
    assert captured["ephemeral"]["branding_tracking_id"]
    assert "Welcome <@U123> to *#contribute*!" in captured["ephemeral"]["text"]
    assert [row[1] for row in captured["logs"]] == [
        "Channel_Join",
        "Channel_Join_Message",
    ]


def test_slack_api_send_ephemeral_adds_tracking_branding_block():
    captured = {}
    original_call = worker.slack_api_call

    async def fake_call(
        env,
        api_method,
        request_payload,
        team_id="",
        channel_id="",
        user_id="",
        app_id="",
        token="",
    ):
        captured["api_method"] = api_method
        captured["payload"] = request_payload
        captured["team_id"] = team_id
        captured["channel_id"] = channel_id
        captured["user_id"] = user_id
        return {"ok": True}

    env = _Env()
    setattr(env, "BASE_URL", "https://sammich.example")
    worker.slack_api_call = fake_call
    try:
        result = asyncio.run(
            worker.slack_api_send_ephemeral(
                "C123",
                "U123",
                "hello",
                env,
                team_id="T123",
                blocks=[worker.make_section_block("hello")],
                branding_tracking_id="tid-123",
            )
        )
    finally:
        worker.slack_api_call = original_call

    assert result["ok"]
    assert captured["api_method"] == "chat.postEphemeral"
    assert captured["payload"]["blocks"][-1]["type"] == "context"
    image_element = captured["payload"]["blocks"][-1]["elements"][0]
    assert image_element["type"] == "image"
    assert "https://sammich.example/logo-hit?" in image_element["image_url"]
    assert "tid=tid-123" in image_element["image_url"]
    assert "ch=C123" in image_element["image_url"]
    assert "u=U123" in image_element["image_url"]


def test_db_mark_join_message_verified_by_tracking_matches_compact_json():
    captured = {}
    original_d1_run = worker.d1_run
    original_schema_ready = worker.SCHEMA_READY

    async def fake_d1_run(env, query, params=None):
        if query.startswith("SELECT id, request_data FROM events"):
            captured["select_query"] = query
            captured["select_params"] = params
            return {
                "results": [
                    {
                        "id": 42,
                        "request_data": '{"logo_tracking_id":"tid-123","kind":"team_join"}',
                    }
                ]
            }
        if query.startswith("UPDATE events SET request_data"):
            captured["update_params"] = params
            return {"success": True}
        return {"success": True}

    env = _Env()
    setattr(env, "DB", object())
    worker.d1_run = fake_d1_run
    worker.SCHEMA_READY = True
    try:
        result = asyncio.run(
            worker.db_mark_join_message_verified_by_tracking(
                env, "tid-123", "203.0.113.7", "Slackbot"
            )
        )
    finally:
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    assert result is True
    assert "Team_Join_Welcome" in captured["select_query"]
    assert captured["select_params"] == ['%"logo_tracking_id"%', '%"tid-123"%']
    updated = json.loads(captured["update_params"][0])
    assert updated["verification_ip"] == "203.0.113.7"
    assert updated["verification_user_agent"] == "Slackbot"
    assert captured["update_params"][1] == 42


def test_blt_welcome_command_sends_welcome_dm():
    captured = {"sent": None, "logs": []}
    original_get_workspace = worker.db_get_workspace_by_team
    original_get_channels = worker.db_get_channels
    original_open = worker.slack_api_open_conversation
    original_send = worker.slack_api_send_message
    original_log = worker.db_log_event

    async def fake_get_workspace(env, team_id):
        return {"id": 7, "team_id": team_id, "team_name": "OWASP"}

    async def fake_get_channels(env, workspace_id):
        return [{"channel_id": "C077QBBLY1Z", "channel_name": "contribute"}]

    async def fake_open(user_id, env, team_id=""):
        return {"ok": True, "channel": {"id": "D123"}}

    async def fake_send(
        channel_id,
        text,
        env,
        team_id="",
        blocks=None,
        branding_tracking_id="",
    ):
        captured["sent"] = {
            "channel_id": channel_id,
            "text": text,
            "team_id": team_id,
            "blocks": blocks,
            "branding_tracking_id": branding_tracking_id,
        }
        return {"ok": True, "ts": "123.456"}

    async def fake_log(env, workspace_id, event_type, **kwargs):
        captured["logs"].append((workspace_id, event_type, kwargs))
        return True

    worker.db_get_workspace_by_team = fake_get_workspace
    worker.db_get_channels = fake_get_channels
    worker.slack_api_open_conversation = fake_open
    worker.slack_api_send_message = fake_send
    worker.db_log_event = fake_log
    try:
        response = asyncio.run(
            worker.command_response(
                {"command": "/blt-welcome", "team_id": "T070JPE5BQQ", "user_id": "U123"},
                _Env(),
            )
        )
    finally:
        worker.db_get_workspace_by_team = original_get_workspace
        worker.db_get_channels = original_get_channels
        worker.slack_api_open_conversation = original_open
        worker.slack_api_send_message = original_send
        worker.db_log_event = original_log

    assert response["response_type"] == "ephemeral"
    assert "sent" in response["text"]
    assert captured["sent"]["channel_id"] == "D123"
    assert captured["sent"]["team_id"] == "T070JPE5BQQ"
    assert captured["sent"]["branding_tracking_id"]
    rendered = captured["sent"]["blocks"][0]["text"]["text"]
    assert "Welcome to the OWASP Slack Community, <@U123>!" in rendered
    assert "<#C077QBBLY1Z|contribute>" in rendered
    assert captured["logs"][0][1] == "Team_Join_Welcome"


def test_handle_team_join_event_uses_joined_users_team_for_real_member_dm():
    captured = {"workspace_lookups": [], "opened": None, "sent": None, "logs": []}
    original_get_workspace = worker.db_get_workspace_by_team
    original_bot_user_id = worker.db_get_workspace_bot_user_id
    original_has_event = worker.db_has_team_join_welcome_event_id
    original_get_channels = worker.db_get_channels
    original_open = worker.slack_api_open_conversation
    original_send = worker.slack_api_send_message
    original_log = worker.db_log_event

    async def fake_get_workspace(env, team_id):
        captured["workspace_lookups"].append(team_id)
        if team_id == "TUSER":
            return {"id": 7, "team_id": team_id, "team_name": "OWASP"}
        return None

    async def fake_bot_user_id(env, team_id="", channel_id=""):
        return "UBOT"

    async def fake_has_event(env, workspace_id, event_id):
        return False

    async def fake_get_channels(env, workspace_id):
        return []

    async def fake_open(user_id, env, team_id=""):
        captured["opened"] = {"user_id": user_id, "team_id": team_id}
        return {"ok": True, "channel": {"id": "D123"}}

    async def fake_send(
        channel_id,
        text,
        env,
        team_id="",
        blocks=None,
        branding_tracking_id="",
    ):
        captured["sent"] = {
            "channel_id": channel_id,
            "team_id": team_id,
            "blocks": blocks,
        }
        return {"ok": True, "ts": "123.456"}

    async def fake_log(env, workspace_id, event_type, **kwargs):
        captured["logs"].append((workspace_id, event_type, kwargs))
        return True

    worker.db_get_workspace_by_team = fake_get_workspace
    worker.db_get_workspace_bot_user_id = fake_bot_user_id
    worker.db_has_team_join_welcome_event_id = fake_has_event
    worker.db_get_channels = fake_get_channels
    worker.slack_api_open_conversation = fake_open
    worker.slack_api_send_message = fake_send
    worker.db_log_event = fake_log
    try:
        result = asyncio.run(
            worker.handle_team_join_event(
                _Env(),
                {"user": {"id": "UREAL", "team_id": "TUSER", "is_bot": False}},
                team_id="TENVELOPE",
                envelope={"event_id": "Ev0B8WD26Q5A", "event_time": 1710000000},
            )
        )
    finally:
        worker.db_get_workspace_by_team = original_get_workspace
        worker.db_get_workspace_bot_user_id = original_bot_user_id
        worker.db_has_team_join_welcome_event_id = original_has_event
        worker.db_get_channels = original_get_channels
        worker.slack_api_open_conversation = original_open
        worker.slack_api_send_message = original_send
        worker.db_log_event = original_log

    assert result == {"ok": True, "action": "team_join_welcome_sent"}
    assert captured["workspace_lookups"][0] == "TUSER"
    assert captured["opened"] == {"user_id": "UREAL", "team_id": "TUSER"}
    assert captured["sent"]["team_id"] == "TUSER"
    assert captured["logs"][0][2]["slack_team_id"] == "TUSER"
    request_data = json.loads(captured["logs"][0][2]["request_data"])
    assert request_data["source_team_id"] == "TENVELOPE"
    assert request_data["user_team_id"] == "TUSER"


def test_handle_team_join_event_skips_bot_user_before_opening_dm():
    captured = {"opened": False, "logs": []}
    original_get_workspace = worker.db_get_workspace_by_team
    original_bot_user_id = worker.db_get_workspace_bot_user_id
    original_open = worker.slack_api_open_conversation
    original_log = worker.db_log_event

    async def fake_get_workspace(env, team_id):
        return {"id": 7, "team_id": team_id, "team_name": "OWASP"}

    async def fake_bot_user_id(env, team_id="", channel_id=""):
        return "UBOT"

    async def fake_open(user_id, env, team_id=""):
        captured["opened"] = True
        return {"ok": True, "channel": {"id": "D123"}}

    async def fake_log(env, workspace_id, event_type, **kwargs):
        captured["logs"].append((workspace_id, event_type, kwargs))
        return True

    worker.db_get_workspace_by_team = fake_get_workspace
    worker.db_get_workspace_bot_user_id = fake_bot_user_id
    worker.slack_api_open_conversation = fake_open
    worker.db_log_event = fake_log
    try:
        result = asyncio.run(
            worker.handle_team_join_event(
                _Env(),
                {"user": {"id": "UBOT", "team_id": "T123", "is_bot": True}},
                team_id="T123",
                envelope={"event_id": "EvBOT", "event_time": 1710000000},
            )
        )
    finally:
        worker.db_get_workspace_by_team = original_get_workspace
        worker.db_get_workspace_bot_user_id = original_bot_user_id
        worker.slack_api_open_conversation = original_open
        worker.db_log_event = original_log

    assert result == {
        "ok": True,
        "action": "team_join_welcome_skipped",
        "reason": "bot_user",
    }
    assert captured["opened"] is False
    assert captured["logs"][0][2]["status"] == "skipped"


def test_db_upsert_slack_app_persists_app_secrets():
    captured = {}
    original_d1_run = worker.d1_run
    original_schema_ready = worker.SCHEMA_READY

    async def fake_d1_run(env, query, params=None):
        if "INSERT INTO slack_apps" in query:
            captured["query"] = query
            captured["params"] = params
            return {"success": True}
        if "SELECT id FROM slack_apps" in query:
            return {"results": [{"id": 7}]}
        return {"success": True}

    env = _Env()
    setattr(env, "DB", object())
    worker.d1_run = fake_d1_run
    worker.SCHEMA_READY = False
    try:
        app_row_id = asyncio.run(
            worker.db_upsert_slack_app(
                env,
                app_id="A123",
                client_id="123.456",
                client_secret="client-secret",
                signing_secret="signing-secret",
                app_token="xapp-token",
                bot_token="xoxb-token",
                bot_user_id="UBOT",
            )
        )
    finally:
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    assert app_row_id == 7
    assert "client_secret" in captured["query"]
    assert "signing_secret" in captured["query"]
    assert captured["params"][0] == "A123"
    assert captured["params"][3] == "123.456"
    assert captured["params"][4] == "client-secret"
    assert captured["params"][5] == "signing-secret"
    assert captured["params"][6] == "xapp-token"
    assert captured["params"][7] == "xoxb-token"
    assert captured["params"][8] == "UBOT"


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
                "slack_apps",
                {
                    "field__app_id": "A123",
                    "field__app_name": "Sammich",
                    "field__app_icon_url": "https://example.com/icon.png",
                    "field__client_id": "123.456",
                    "field__client_secret": "client-secret",
                    "field__signing_secret": "signing-secret",
                    "field__app_token": "xapp-token",
                    "field__bot_token": "xoxb-token",
                    "field__bot_user_id": "UBOT",
                    "field__manifest_yaml": "display_information:",
                    "field__created_at": "2026-06-06T00:00:00+00:00",
                    "field__updated_at": "2026-06-06T00:00:00+00:00",
                },
            )
        )
        asyncio.run(
            worker.db_admin_update_row(
                env,
                "slack_apps",
                "7",
                {
                    "field__app_id": "A123",
                    "field__app_name": "Sammich 2",
                    "field__app_icon_url": "https://example.com/icon.png",
                    "field__client_id": "123.456",
                    "field__client_secret": "client-secret",
                    "field__signing_secret": "signing-secret",
                    "field__app_token": "xapp-token",
                    "field__bot_token": "xoxb-token",
                    "field__bot_user_id": "UBOT",
                    "field__manifest_yaml": "display_information:",
                    "field__created_at": "2026-06-06T00:00:00+00:00",
                    "field__updated_at": "2026-06-06T01:00:00+00:00",
                },
            )
        )
        asyncio.run(worker.db_admin_delete_row(env, "slack_apps", "7"))
    finally:
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    assert captured[0][0].startswith("INSERT INTO slack_apps")
    inserted_columns = [
        column.strip()
        for column in captured[0][0].split("(", 1)[1].split(")", 1)[0].split(",")
    ]
    assert "id" not in inserted_columns
    assert captured[0][1][0] == "A123"
    assert captured[1][0].startswith("UPDATE slack_apps SET")
    assert captured[1][1][-1] == "7"
    assert captured[2] == ("DELETE FROM slack_apps WHERE id = ?", ["7"])


def test_db_admin_related_tree_nests_cascade_records():
    original_d1_run = worker.d1_run
    original_schema_ready = worker.SCHEMA_READY

    async def fake_d1_run(env, query, params=None):
        if "FROM channels WHERE workspace_id" in query:
            return {
                "results": [
                    {
                        "id": 10,
                        "workspace_id": 1,
                        "channel_id": "C123",
                        "channel_name": "general",
                    }
                ]
            }
        return {"results": []}

    env = _Env()
    setattr(env, "DB", object())
    worker.d1_run = fake_d1_run
    worker.SCHEMA_READY = False
    try:
        related = asyncio.run(
            worker.db_admin_related_tree(
                env,
                "teams",
                {"id": 1, "team_id": "T123", "team_name": "Security Team"},
            )
        )
    finally:
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    rendered = worker.render_admin_cascade_tree(related)
    assert "channels" in rendered
    assert "channels.id 10" in rendered
    assert "user_workspaces" not in rendered
    assert "connected_workspaces" not in rendered
    assert worker.admin_cascade_count(related) == 1


def test_db_admin_confirmed_delete_cascades_children_before_parent():
    captured = []
    original_d1_run = worker.d1_run
    original_schema_ready = worker.SCHEMA_READY

    async def fake_d1_run(env, query, params=None):
        captured.append((query, params))
        if "SELECT * FROM teams WHERE id = ?" in query:
            return {"results": [{"id": 1, "team_id": "T123", "team_name": "Security Team"}]}
        if "SELECT * FROM channels WHERE id = ?" in query:
            return {"results": [{"id": 10, "workspace_id": 1, "channel_id": "C123"}]}
        if "SELECT * FROM channels WHERE workspace_id = ?" in query:
            return {"results": [{"id": 10, "workspace_id": 1, "channel_id": "C123"}]}
        return {"results": []}

    env = _Env()
    setattr(env, "DB", object())
    worker.d1_run = fake_d1_run
    worker.SCHEMA_READY = False
    try:
        asyncio.run(worker.db_admin_delete_row_cascade(env, "teams", "1"))
    finally:
        worker.d1_run = original_d1_run
        worker.SCHEMA_READY = original_schema_ready

    delete_queries = [query for query, _ in captured if query.startswith("DELETE FROM")]
    assert "DELETE FROM channels WHERE id = ?" in delete_queries
    assert delete_queries[-1] == "DELETE FROM teams WHERE id = ?"


def test_admin_bulk_delete_action_deletes_each_selected_row():
    deleted = []
    original_delete = worker.db_admin_delete_row_cascade

    async def fake_delete(env, table_name, pk_value):
        deleted.append((table_name, pk_value))

    env = _Env()
    setattr(env, "ADMIN_URL", "/private-admin")
    worker.db_admin_delete_row_cascade = fake_delete
    try:
        asyncio.run(
            worker.handle_admin_form_action(
                env,
                {
                    "action": "db_bulk_delete",
                    "table": "channels",
                    "row_pk__0": "1",
                    "row_pk__1": "2",
                    "row_pk__2": "1",
                },
            )
        )
    finally:
        worker.db_admin_delete_row_cascade = original_delete

    assert deleted == [("channels", "1"), ("channels", "2")]


def test_db_admin_rejects_unknown_table_names():
    try:
        worker.require_admin_table_name("slack_apps; DROP TABLE users")
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
    original_direct_response = worker.slack_api_post_direct_response
    original_json_response = worker.json_response

    async def fake_direct_response(event, text, env, team_id="", app_id=""):
        sent["channel_id"] = event.get("channel")
        sent["text"] = text
        sent["team_id"] = team_id
        sent["app_id"] = app_id
        return {"ok": True}

    worker.slack_api_post_direct_response = fake_direct_response
    worker.json_response = lambda payload, status=200, headers=None: payload
    try:
        asyncio.run(
            worker.handle_event_payload(
                {
                    "type": "event_callback",
                    "api_app_id": "A089A036135",
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
        worker.slack_api_post_direct_response = original_direct_response
        worker.json_response = original_json_response

    assert sent["channel_id"] == "D123"
    assert sent["team_id"] == "T123"
    assert sent["app_id"] == "A089A036135"
    assert "/stats" in sent["text"]


def test_handle_event_payload_replies_to_direct_message_when_db_lookups_fail():
    sent = {}
    original_direct_response = worker.slack_api_post_direct_response
    original_bot_user_id = worker.db_get_workspace_bot_user_id
    original_installer = worker.get_workspace_installer
    original_json_response = worker.json_response

    async def fake_direct_response(event, text, env, team_id="", app_id=""):
        sent["channel_id"] = event.get("channel")
        sent["text"] = text
        sent["team_id"] = team_id
        sent["app_id"] = app_id
        return {"ok": True}

    async def failing_bot_user_id(env, team_id="", channel_id="", app_id=""):
        raise RuntimeError("D1 unavailable")

    async def failing_installer(env, team_id):
        raise RuntimeError("D1 unavailable")

    worker.slack_api_post_direct_response = fake_direct_response
    worker.db_get_workspace_bot_user_id = failing_bot_user_id
    worker.get_workspace_installer = failing_installer
    worker.json_response = lambda payload, status=200, headers=None: payload
    try:
        asyncio.run(
            worker.handle_event_payload(
                {
                    "type": "event_callback",
                    "api_app_id": "A089A036135",
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
        worker.slack_api_post_direct_response = original_direct_response
        worker.db_get_workspace_bot_user_id = original_bot_user_id
        worker.get_workspace_installer = original_installer
        worker.json_response = original_json_response

    assert sent["channel_id"] == "D123"
    assert sent["team_id"] == "T123"
    assert sent["app_id"] == "A089A036135"
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
        response = asyncio.run(
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
    assert response == {"ok": True}


def test_handle_event_payload_acknowledges_app_home_publish_errors():
    original_publish_home = worker.slack_api_publish_home
    original_json_response = worker.json_response

    async def fake_publish_home(user_id, env, team_id=""):
        raise RuntimeError("views.publish failed")

    worker.slack_api_publish_home = fake_publish_home
    worker.json_response = lambda payload, status=200, headers=None: payload
    try:
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            response = asyncio.run(
                worker.handle_event_payload(
                    {
                        "type": "event_callback",
                        "team_id": "T123",
                        "event": {
                            "type": "app_home_opened",
                            "user": "U123",
                            "tab": "home",
                        },
                    },
                    _Env(),
                )
            )
    finally:
        worker.slack_api_publish_home = original_publish_home
        worker.json_response = original_json_response

    assert response == {"ok": True}
    assert "app_home_publish_failed" in captured.getvalue()
    assert "views.publish failed" in captured.getvalue()


def test_slack_api_publish_home_uses_views_publish_shape():
    captured = {}
    original_fetch_json = worker.fetch_json
    original_log_response = worker.log_slack_api_response
    original_get_workspace = worker.db_get_workspace_by_team
    original_bot_token = worker.db_get_workspace_bot_token
    original_bot_user_id = worker.db_get_workspace_bot_user_id

    async def fake_fetch_json(url, method="GET", headers=None, body=None):
        captured.setdefault("urls", []).append(url)
        if url == "https://slack.com/api/auth.test":
            return True, {"ok": True, "user_id": "UBOT"}, 200
        captured["url"] = url
        captured["method"] = method
        captured["headers"] = headers
        captured["body"] = json.loads(body or "{}")
        return True, {"ok": True}, 200

    async def fake_log_response(*args, **kwargs):
        captured["logged"] = True

    async def fake_get_workspace(env, team_id):
        return {"id": 7, "team_id": team_id, "team_name": "OWASP"}

    async def fake_bot_token(env, team_id="", channel_id="", app_id=""):
        captured["token_app_id"] = app_id
        return "xoxb-token"

    async def fake_bot_user_id(env, team_id="", channel_id=""):
        return "UBOT"

    worker.fetch_json = fake_fetch_json
    worker.log_slack_api_response = fake_log_response
    worker.db_get_workspace_by_team = fake_get_workspace
    worker.db_get_workspace_bot_token = fake_bot_token
    worker.db_get_workspace_bot_user_id = fake_bot_user_id
    try:
        env = _Env()
        setattr(env, "BASE_URL", "https://sammich.example")
        setattr(env, "APP_VERSION", "9.8.7")
        asyncio.run(worker.slack_api_publish_home("U123", env, team_id="T123"))
    finally:
        worker.fetch_json = original_fetch_json
        worker.log_slack_api_response = original_log_response
        worker.db_get_workspace_by_team = original_get_workspace
        worker.db_get_workspace_bot_token = original_bot_token
        worker.db_get_workspace_bot_user_id = original_bot_user_id

    assert captured["url"] == "https://slack.com/api/views.publish"
    assert captured["method"] == "POST"
    assert captured["headers"]["Authorization"] == "Bearer xoxb-token"
    assert captured["headers"]["Content-Type"] == "application/json; charset=utf-8"
    assert captured["body"]["user_id"] == "U123"
    assert captured["body"]["view"]["type"] == "home"
    encoded_view = str(captured["body"]["view"])
    assert "/stats" in encoded_view
    assert "Welcome to BLT Sammich, <@U123>" in encoded_view
    assert "OWASP" in encoded_view
    assert "https://sammich.example" in encoded_view
    assert "Running version `9.8.7`" in encoded_view
    assert captured["logged"] is True


def test_slack_api_publish_home_skips_bot_user_from_auth_test():
    captured = {"urls": [], "updates": []}
    original_fetch_json = worker.fetch_json
    original_log_response = worker.log_slack_api_response
    original_bot_token = worker.db_get_workspace_bot_token
    original_bot_user_id = worker.db_get_workspace_bot_user_id
    original_update_bot_user_id = worker.db_update_workspace_bot_user_id

    async def fake_fetch_json(url, method="GET", headers=None, body=None):
        captured["urls"].append(url)
        if url == "https://slack.com/api/auth.test":
            return True, {"ok": True, "user_id": "U04TJF11F"}, 200
        return True, {"ok": True}, 200

    async def fake_log_response(*args, **kwargs):
        captured["logged"] = True

    async def fake_bot_token(env, team_id="", channel_id="", app_id=""):
        captured["token_app_id"] = app_id
        return "xoxb-token"

    async def fake_bot_user_id(env, team_id="", channel_id=""):
        return ""

    async def fake_update_bot_user_id(env, team_id, bot_user_id):
        captured["updates"].append((team_id, bot_user_id))
        return True

    worker.fetch_json = fake_fetch_json
    worker.log_slack_api_response = fake_log_response
    worker.db_get_workspace_bot_token = fake_bot_token
    worker.db_get_workspace_bot_user_id = fake_bot_user_id
    worker.db_update_workspace_bot_user_id = fake_update_bot_user_id
    try:
        asyncio.run(
            worker.slack_api_publish_home(
                "U04TJF11F", _Env(), team_id="T04T40NHX"
            )
        )
    finally:
        worker.fetch_json = original_fetch_json
        worker.log_slack_api_response = original_log_response
        worker.db_get_workspace_bot_token = original_bot_token
        worker.db_get_workspace_bot_user_id = original_bot_user_id
        worker.db_update_workspace_bot_user_id = original_update_bot_user_id

    assert captured["urls"] == ["https://slack.com/api/auth.test"]
    assert captured["updates"] == [("T04T40NHX", "U04TJF11F")]
    assert "logged" not in captured


def test_slack_api_publish_home_skips_invalid_home_user_response():
    captured = {"logged": False}
    original_fetch_json = worker.fetch_json
    original_log_response = worker.log_slack_api_response
    original_bot_token = worker.db_get_workspace_bot_token
    original_bot_user_id = worker.db_get_workspace_bot_user_id

    async def fake_fetch_json(url, method="GET", headers=None, body=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = json.loads(body or "{}")
        return (
            True,
            {
                "ok": False,
                "error": "invalid_arguments",
                "response_metadata": {
                    "messages": ["[ERROR] invalid `user_id`"],
                    "warnings": ["missing_charset"],
                },
                "warning": "missing_charset",
            },
            200,
        )

    async def fake_log_response(*args, **kwargs):
        captured["logged"] = True

    async def fake_bot_token(env, team_id="", channel_id="", app_id=""):
        captured["token_app_id"] = app_id
        return "xoxb-token"

    async def fake_bot_user_id(env, team_id="", channel_id=""):
        return "UBOT"

    worker.fetch_json = fake_fetch_json
    worker.log_slack_api_response = fake_log_response
    worker.db_get_workspace_bot_token = fake_bot_token
    worker.db_get_workspace_bot_user_id = fake_bot_user_id
    try:
        asyncio.run(
            worker.slack_api_publish_home(
                "U04TJF11F", _Env(), team_id="T04T40NHX"
            )
        )
    finally:
        worker.fetch_json = original_fetch_json
        worker.log_slack_api_response = original_log_response
        worker.db_get_workspace_bot_token = original_bot_token
        worker.db_get_workspace_bot_user_id = original_bot_user_id

    assert captured["url"] == "https://slack.com/api/views.publish"
    assert captured["headers"]["Content-Type"] == "application/json; charset=utf-8"
    assert captured["body"]["user_id"] == "U04TJF11F"
    assert captured["logged"] is False


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
        app_id,
        api_method,
        request_payload,
        response_payload,
        ok,
        status_code,
    ):
        captured["log"] = {
            "team_id": team_id,
            "channel_id": channel_id,
            "app_id": app_id,
            "api_method": api_method,
            "request_payload": request_payload,
            "response_payload": response_payload,
            "ok": ok,
            "status_code": status_code,
        }

    async def fake_bot_token(env, team_id="", channel_id="", app_id=""):
        captured["token_app_id"] = app_id
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
                app_id="A089A036135",
            )
        )
    finally:
        worker.fetch_json = original_fetch_json
        worker.log_slack_api_response = original_log_response
        worker.db_get_workspace_bot_token = original_bot_token

    assert captured["url"] == "https://slack.com/api/chat.postMessage"
    assert captured["log"]["team_id"] == "T123"
    assert captured["log"]["channel_id"] == "C123"
    assert captured["log"]["app_id"] == "A089A036135"
    assert captured["log"]["api_method"] == "chat.postMessage"
    assert captured["log"]["response_payload"] == {"ok": True, "ts": "123.456"}
    assert captured["log"]["ok"] is True
    assert captured["token_app_id"] == "A089A036135"


def test_slack_api_post_direct_response_reopens_dm_when_channel_missing():
    captured = {"posts": [], "opened": None}
    original_post_message = worker.slack_api_post_message
    original_open = worker.slack_api_open_conversation

    async def fake_post_message(channel_id, text, env, team_id="", app_id=""):
        captured["posts"].append(
            {
                "channel_id": channel_id,
                "text": text,
                "team_id": team_id,
                "app_id": app_id,
            }
        )
        if channel_id == "DOLD":
            return {"ok": False, "error": "channel_not_found"}
        return {"ok": True, "channel": channel_id}

    async def fake_open(user_id, env, team_id="", app_id=""):
        captured["opened"] = {"user_id": user_id, "team_id": team_id, "app_id": app_id}
        return {"ok": True, "channel": {"id": "DNEW"}}

    worker.slack_api_post_message = fake_post_message
    worker.slack_api_open_conversation = fake_open
    try:
        result = asyncio.run(
            worker.slack_api_post_direct_response(
                {"channel": "DOLD", "user": "U04TJF11F"},
                "Available commands:",
                _Env(),
                team_id="T04T40NHX",
                app_id="A089A036135",
            )
        )
    finally:
        worker.slack_api_post_message = original_post_message
        worker.slack_api_open_conversation = original_open

    assert result["ok"] is True
    assert captured["opened"] == {
        "user_id": "U04TJF11F",
        "team_id": "T04T40NHX",
        "app_id": "A089A036135",
    }
    assert [post["channel_id"] for post in captured["posts"]] == ["DOLD", "DNEW"]
    assert captured["posts"][1]["app_id"] == "A089A036135"


def test_slack_api_post_direct_response_uses_env_token_when_db_token_cannot_see_dm():
    captured = {"calls": []}
    original_call = worker.slack_api_call

    async def fake_call(
        env,
        api_method,
        request_payload,
        team_id="",
        channel_id="",
        user_id="",
        app_id="",
        token="",
    ):
        captured["calls"].append(
            {
                "api_method": api_method,
                "request": request_payload,
                "team_id": team_id,
                "channel_id": channel_id,
                "user_id": user_id,
                "app_id": app_id,
                "token": token,
            }
        )
        if api_method == "chat.postMessage" and token == "":
            return {"ok": False, "error": "channel_not_found"}
        if api_method == "chat.postMessage" and token == "xoxb-env-current":
            return {"ok": True, "ts": "123.456"}
        return {"ok": False, "error": "unexpected_call"}

    env = _Env()
    setattr(env, "SLACK_BOT_TOKEN", "xoxb-env-current")
    worker.slack_api_call = fake_call
    try:
        result = asyncio.run(
            worker.slack_api_post_direct_response(
                {"channel": "D089KE85SE9", "user": "U04TJF11F"},
                "Available commands:",
                env,
                team_id="T04T40NHX",
                app_id="A089A036135",
            )
        )
    finally:
        worker.slack_api_call = original_call

    assert result == {"ok": True, "ts": "123.456"}
    assert [call["api_method"] for call in captured["calls"]] == [
        "chat.postMessage",
        "chat.postMessage",
    ]
    assert captured["calls"][0]["token"] == ""
    assert captured["calls"][1]["token"] == "xoxb-env-current"
    assert captured["calls"][1]["channel_id"] == "D089KE85SE9"
    assert captured["calls"][1]["app_id"] == "A089A036135"


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

    async def failing_bot_token(env, team_id="", channel_id="", app_id=""):
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
    original_direct_response = worker.slack_api_post_direct_response
    original_bot_user_id = worker.db_get_workspace_bot_user_id
    original_json_response = worker.json_response

    async def fake_direct_response(event, text, env, team_id="", app_id=""):
        sent["channel_id"] = event.get("channel")
        sent["text"] = text
        sent["team_id"] = team_id
        sent["app_id"] = app_id
        return {"ok": True}

    async def fake_bot_user_id(env, team_id="", channel_id="", app_id=""):
        sent["lookup_app_id"] = app_id
        return "U999"

    worker.slack_api_post_direct_response = fake_direct_response
    worker.db_get_workspace_bot_user_id = fake_bot_user_id
    worker.json_response = lambda payload, status=200, headers=None: payload
    try:
        asyncio.run(
            worker.handle_event_payload(
                {
                    "type": "event_callback",
                    "api_app_id": "A089A036135",
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
        worker.slack_api_post_direct_response = original_direct_response
        worker.db_get_workspace_bot_user_id = original_bot_user_id
        worker.json_response = original_json_response

    assert sent["channel_id"] == "C123"
    assert sent["team_id"] == "T123"
    assert sent["app_id"] == "A089A036135"
    assert sent["lookup_app_id"] == "A089A036135"
    assert "/stats" in sent["text"]


def test_handle_event_payload_does_not_reply_to_bot_self_message():
    sent = {}
    original_direct_response = worker.slack_api_post_direct_response
    original_bot_user_id = worker.db_get_workspace_bot_user_id
    original_json_response = worker.json_response

    async def fake_direct_response(event, text, env, team_id="", app_id=""):
        sent["channel_id"] = event.get("channel")
        return {"ok": True}

    async def fake_bot_user_id(env, team_id="", channel_id="", app_id=""):
        return "U999"

    worker.slack_api_post_direct_response = fake_direct_response
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
        worker.slack_api_post_direct_response = original_direct_response
        worker.db_get_workspace_bot_user_id = original_bot_user_id
        worker.json_response = original_json_response

    assert sent == {}
