"""Tests for worker utility functions."""


def test_verify_oauth_state_valid():
    """Test OAuth state verification with valid state."""
    # Import inline to avoid Cloudflare runtime dependencies
    import sys
    from unittest.mock import Mock

    # Mock the worker module
    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src.worker import _verify_oauth_state

    state = "signin:abc123"
    result = _verify_oauth_state(state, state)

    assert result == "signin"


def test_verify_oauth_state_invalid():
    """Test OAuth state verification with invalid state."""
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src.worker import _verify_oauth_state

    stored = "signin:abc123"
    received = "signin:xyz789"
    result = _verify_oauth_state(stored, received)

    assert result is None


def test_verify_oauth_state_missing():
    """Test OAuth state verification with missing states."""
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src.worker import _verify_oauth_state

    result = _verify_oauth_state("", "signin:abc123")
    assert result is None

    result = _verify_oauth_state("signin:abc123", "")
    assert result is None


def test_get_utc_now():
    """Test UTC timestamp generation."""
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src.worker import get_utc_now

    timestamp = get_utc_now()

    assert isinstance(timestamp, str)
    assert "T" in timestamp
    assert timestamp.endswith("+00:00") or timestamp.endswith("Z")


def test_parse_cookies():
    """Test cookie parsing from headers."""
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src.worker import parse_cookies

    # Mock request object
    request = Mock()
    request.headers = {"Cookie": "session_id=abc123; oauth_state=signin:xyz789"}

    cookies = parse_cookies(request)

    assert "session_id" in cookies
    assert cookies["session_id"] == "abc123"
    assert "oauth_state" in cookies
    assert cookies["oauth_state"] == "signin:xyz789"


def test_parse_cookies_empty():
    """Test cookie parsing with no cookies."""
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src.worker import parse_cookies

    request = Mock()
    request.headers = {}

    cookies = parse_cookies(request)

    assert cookies == {}


def test_is_valid_slack_url():
    """Test Slack URL validation."""
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src.worker import is_valid_slack_url

    assert is_valid_slack_url("https://hooks.slack.com/services/ABC123")
    assert is_valid_slack_url("https://slack.com/api/oauth.v2.access")
    assert not is_valid_slack_url("https://evil.com/phishing")
    assert not is_valid_slack_url("javascript:alert(1)")
    assert not is_valid_slack_url("ftp://slack.com")


def test_welcome_message_formatting():
    """Test welcome message generation."""
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src.worker import WELCOME_MESSAGE

    user_id = "U12345"
    message = WELCOME_MESSAGE.format(user_id=user_id)

    assert "<@U12345>" in message
    assert "Welcome to the open-source community" in message


def test_handle_app_link_command_uses_workspace_app_id():
    """App link command should use app_id from workspace record when available."""
    import asyncio
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src import worker

    async def _fake_db_get_workspace_by_team_and_app(_env, _team_id, _app_id):
        return {"app_id": "A_FROM_DB"}

    original = worker.db_get_workspace_by_team_and_app
    worker.db_get_workspace_by_team_and_app = _fake_db_get_workspace_by_team_and_app
    try:
        env = Mock()
        env.SLACK_APP_ID = ""
        body = {"team_id": "T123", "api_app_id": ""}
        result = asyncio.run(worker._handle_app_link_command(env, body))
    finally:
        worker.db_get_workspace_by_team_and_app = original

    assert result["response_type"] == "ephemeral"
    assert "https://api.slack.com/apps/A_FROM_DB" in result["text"]


def test_handle_app_link_command_falls_back_to_env_app_id():
    """App link command should use env app id when workspace app_id is missing."""
    import asyncio
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src import worker

    async def _fake_db_get_workspace_by_team_and_app(_env, _team_id, _app_id):
        return {"app_id": ""}

    original = worker.db_get_workspace_by_team_and_app
    worker.db_get_workspace_by_team_and_app = _fake_db_get_workspace_by_team_and_app
    try:
        env = Mock()
        env.SLACK_APP_ID = "A_FROM_ENV"
        body = {"team_id": "T123", "api_app_id": ""}
        result = asyncio.run(worker._handle_app_link_command(env, body))
    finally:
        worker.db_get_workspace_by_team_and_app = original

    assert result["response_type"] == "ephemeral"
    assert "https://api.slack.com/apps/A_FROM_ENV" in result["text"]


def test_handle_app_link_command_reports_missing_app_id():
    """App link command should return clear message when no app_id is available."""
    import asyncio
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src import worker

    async def _fake_db_get_workspace_by_team_and_app(_env, _team_id, _app_id):
        return None

    original = worker.db_get_workspace_by_team_and_app
    worker.db_get_workspace_by_team_and_app = _fake_db_get_workspace_by_team_and_app
    try:
        env = Mock()
        env.SLACK_APP_ID = ""
        body = {"team_id": "T123", "api_app_id": ""}
        result = asyncio.run(worker._handle_app_link_command(env, body))
    finally:
        worker.db_get_workspace_by_team_and_app = original

    assert result["response_type"] == "ephemeral"
    assert "not configured" in result["text"].lower()


def test_handle_set_invite_command_saves_link_for_admin():
    """Invite command should save a valid Slack invite link for admin user."""
    import asyncio
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src import worker

    async def _fake_db_get_workspace_by_team(_env, _team_id):
        return {"id": 7, "team_name": "Test Team"}

    async def _fake_is_workspace_admin_user(_env, _workspace, _user_id):
        return True

    async def _fake_db_update_workspace_invite_link(_env, _workspace_id, _invite_link):
        return True

    orig_get_ws = worker.db_get_workspace_by_team
    orig_is_admin = worker._is_workspace_admin_user
    orig_update = worker.db_update_workspace_invite_link
    worker.db_get_workspace_by_team = _fake_db_get_workspace_by_team
    worker._is_workspace_admin_user = _fake_is_workspace_admin_user
    worker.db_update_workspace_invite_link = _fake_db_update_workspace_invite_link
    try:
        env = Mock()
        body = {
            "team_id": "T123",
            "user_id": "U123",
            "text": "https://join.slack.com/t/test/shared_invite/abc",
        }
        result = asyncio.run(worker._handle_set_invite_command(env, body))
    finally:
        worker.db_get_workspace_by_team = orig_get_ws
        worker._is_workspace_admin_user = orig_is_admin
        worker.db_update_workspace_invite_link = orig_update

    assert result["response_type"] == "ephemeral"
    assert "invite link saved" in result["text"].lower()


def test_welcome_command_links_channels_clickably():
    """/lettuce-welcome should render #channel references as clickable channel mentions."""
    import asyncio
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src import worker

    async def _fake_db_get_workspace_by_team(_env, _team_id):
        return {"id": 6}

    async def _fake_db_get_channels(_env, _workspace_id):
        return [
            {"channel_id": "CGEN", "channel_name": "general"},
            {"channel_id": "CHELP", "channel_name": "help"},
        ]

    original_get_workspace_welcome_message = worker.get_workspace_welcome_message
    original_db_get_workspace_by_team = worker.db_get_workspace_by_team
    original_db_get_channels = worker.db_get_channels

    worker.get_workspace_welcome_message = (
        lambda _team_id: "Hi <@{user_id}>! Start in #general and ask in #help."
    )
    worker.db_get_workspace_by_team = _fake_db_get_workspace_by_team
    worker.db_get_channels = _fake_db_get_channels

    try:
        env = Mock()
        body = {"user_id": "U123", "team_id": "T123"}
        result = asyncio.run(worker._handle_welcome_command(env, body))
    finally:
        worker.get_workspace_welcome_message = original_get_workspace_welcome_message
        worker.db_get_workspace_by_team = original_db_get_workspace_by_team
        worker.db_get_channels = original_db_get_channels

    assert result["response_type"] == "ephemeral"
    text = result["text"]
    assert "<#CGEN|general>" in text
    assert "<#CHELP|help>" in text


def test_build_public_events_hides_sensitive_fields_and_keeps_verified():
    """Public events payload should hide sensitive fields and expose verified."""
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src.worker import build_public_events

    events = [
        {
            "id": 10,
            "event_type": "Channel_Join_Message",
            "user_slack_id": "U123",
            "channel_name": "general",
            "request_data": '{"secret":"value"}',
            "status": "success",
            "verified": 1,
            "created_at": "2026-03-22T20:00:00+00:00",
        }
    ]

    public_events = build_public_events(events)

    assert len(public_events) == 1
    row = public_events[0]
    assert row["id"] == 10
    assert row["event_type"] == "Channel_Join_Message"
    assert row["status"] == "success"
    assert row["verified"] == 1
    assert row["created_at"] == "2026-03-22T20:00:00+00:00"
    assert "user_slack_id" not in row
    assert "channel_name" not in row
    assert "request_data" not in row


def test_handle_set_invite_command_rejects_invalid_url():
    """Invite command should reject non-Slack URLs."""
    import asyncio
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src import worker

    async def _fake_db_get_workspace_by_team(_env, _team_id):
        return {"id": 7, "team_name": "Test Team"}

    async def _fake_is_workspace_admin_user(_env, _workspace, _user_id):
        return True

    orig_get_ws = worker.db_get_workspace_by_team
    orig_is_admin = worker._is_workspace_admin_user
    worker.db_get_workspace_by_team = _fake_db_get_workspace_by_team
    worker._is_workspace_admin_user = _fake_is_workspace_admin_user
    try:
        env = Mock()
        body = {
            "team_id": "T123",
            "user_id": "U123",
            "text": "https://example.com/invite",
        }
        result = asyncio.run(worker._handle_set_invite_command(env, body))
    finally:
        worker.db_get_workspace_by_team = orig_get_ws
        worker._is_workspace_admin_user = orig_is_admin

    assert result["response_type"] == "ephemeral"
    assert "valid slack https url" in result["text"].lower()


def test_handle_settings_command_shows_commands_and_current_settings():
    """Settings command should include both command list and workspace settings."""
    import asyncio
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src import worker

    async def _fake_db_get_workspace_by_team(_env, _team_id):
        return {"id": 7, "team_name": "Test Team", "app_id": "A123"}

    async def _fake_db_get_workspace_github_org_count(_env, _workspace_id):
        return 1

    async def _fake_db_get_workspace_latest_org_login(_env, _workspace_id):
        return "OWASP-BLT"

    async def _fake_db_get_workspace_invite_link(_env, _workspace_id):
        return "https://join.slack.com/t/test/shared_invite/abc"

    orig_get_ws = worker.db_get_workspace_by_team
    orig_org_count = worker.db_get_workspace_github_org_count
    orig_org_login = worker.db_get_workspace_latest_org_login
    orig_invite = worker.db_get_workspace_invite_link
    worker.db_get_workspace_by_team = _fake_db_get_workspace_by_team
    worker.db_get_workspace_github_org_count = _fake_db_get_workspace_github_org_count
    worker.db_get_workspace_latest_org_login = _fake_db_get_workspace_latest_org_login
    worker.db_get_workspace_invite_link = _fake_db_get_workspace_invite_link
    try:
        env = Mock()
        body = {"team_id": "T123"}
        result = asyncio.run(worker._handle_settings_command(env, body))
    finally:
        worker.db_get_workspace_by_team = orig_get_ws
        worker.db_get_workspace_github_org_count = orig_org_count
        worker.db_get_workspace_latest_org_login = orig_org_login
        worker.db_get_workspace_invite_link = orig_invite

    assert result["response_type"] == "ephemeral"
    text = result["text"]
    assert "/lettuce-settings" in text
    assert "Current Settings" in text
    assert "OWASP-BLT" in text
    assert "join.slack.com" in text


def test_run_workspace_metrics_sync_uses_full_workspace_for_alert_target():
    """Cron missing-config alerts should hydrate full workspace data before notifying."""
    import asyncio
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src import worker

    captured = {}

    async def _fake_get_workspaces_with_activity_markers(_env):
        return [{"id": 9, "team_name": "Partial WS", "access_token": "xoxb-token"}]

    async def _fake_db_get_repositories(_env, _ws_id):
        return []

    async def _fake_db_get_channels(_env, _ws_id):
        return []

    async def _fake_scan_workspace_channels(_env, _ws_id, _token):
        return None

    async def _fake_fetch_workspace_member_count(_token):
        return 0

    async def _fake_update_counts(_env, _ws_id, channel_count=0, member_count=0):
        return True

    async def _fake_org_count(_env, _ws_id):
        return 0

    async def _fake_invite_link(_env, _ws_id):
        return ""

    async def _fake_db_get_workspace_by_id(_env, _ws_id):
        return {
            "id": 9,
            "team_name": "Hydrated WS",
            "access_token": "xoxb-token",
            "installer_slack_user_id": "U123",
            "installer_name": "Installer",
        }

    async def _fake_send_missing_alert(
        _env, ws, repo_count=0, missing_org=True, missing_invite=False
    ):
        captured["workspace_name"] = ws.get("team_name")
        captured["installer_slack_user_id"] = ws.get("installer_slack_user_id")
        captured["missing_org"] = missing_org
        captured["missing_invite"] = missing_invite
        return {"ok": True}

    orig_get_markers = worker.db_get_workspaces_with_activity_markers
    orig_get_repos = worker.db_get_repositories
    orig_get_channels = worker.db_get_channels
    orig_scan_channels = worker.scan_workspace_channels
    orig_member_count = worker.fetch_workspace_member_count
    orig_update_counts = worker.db_update_workspace_channel_member_counts
    orig_org_count = worker.db_get_workspace_github_org_count
    orig_invite = worker.db_get_workspace_invite_link
    orig_get_by_id = worker.db_get_workspace_by_id
    orig_send_alert = worker.send_missing_github_org_alert

    worker.db_get_workspaces_with_activity_markers = (
        _fake_get_workspaces_with_activity_markers
    )
    worker.db_get_repositories = _fake_db_get_repositories
    worker.db_get_channels = _fake_db_get_channels
    worker.scan_workspace_channels = _fake_scan_workspace_channels
    worker.fetch_workspace_member_count = _fake_fetch_workspace_member_count
    worker.db_update_workspace_channel_member_counts = _fake_update_counts
    worker.db_get_workspace_github_org_count = _fake_org_count
    worker.db_get_workspace_invite_link = _fake_invite_link
    worker.db_get_workspace_by_id = _fake_db_get_workspace_by_id
    worker.send_missing_github_org_alert = _fake_send_missing_alert

    try:
        env = Mock()
        result = asyncio.run(worker.run_workspace_metrics_sync(env))
    finally:
        worker.db_get_workspaces_with_activity_markers = orig_get_markers
        worker.db_get_repositories = orig_get_repos
        worker.db_get_channels = orig_get_channels
        worker.scan_workspace_channels = orig_scan_channels
        worker.fetch_workspace_member_count = orig_member_count
        worker.db_update_workspace_channel_member_counts = orig_update_counts
        worker.db_get_workspace_github_org_count = orig_org_count
        worker.db_get_workspace_invite_link = orig_invite
        worker.db_get_workspace_by_id = orig_get_by_id
        worker.send_missing_github_org_alert = orig_send_alert

    assert result["processed"] == 1
    assert result["alerted"] == 1
    assert captured["workspace_name"] == "Hydrated WS"
    assert captured["installer_slack_user_id"] == "U123"
    assert captured["missing_org"] is True
    assert captured["missing_invite"] is True


def test_send_slack_message_plain_text_does_not_include_blocks():
    """Plain-text Slack messages should not include branding-only blocks."""
    import asyncio
    import json
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src import worker

    captured_payload = {}

    class _FakeHeaders:
        def __init__(self):
            self.values = {}

        def set(self, key, value):
            self.values[key] = value

    class _FakeResponse:
        async def json(self):
            return {"ok": True}

    async def _fake_fetch(_url, options):
        captured_payload.update(json.loads(options.get("body") or "{}"))
        return _FakeResponse()

    original_headers = worker.Headers
    original_fetch = worker.js_fetch
    worker.Headers = type("HeadersShim", (), {"new": staticmethod(_FakeHeaders)})
    worker.js_fetch = _fake_fetch

    try:
        env = Mock()
        env.SLACK_TOKEN = "xoxb-test-token"
        result = asyncio.run(
            worker.send_slack_message(env, "D123", "hello world", blocks=None)
        )
    finally:
        worker.Headers = original_headers
        worker.js_fetch = original_fetch

    assert result.get("ok") is True
    assert captured_payload.get("text") == "hello world"
    assert "blocks" not in captured_payload


def test_resolve_team_id_from_payload_prefers_top_level_team_id():
    """Team ID should come from top-level team_id when present."""
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src.worker import _resolve_team_id_from_payload

    payload = {"team_id": "T_TOP"}
    event = {"team": "T_EVENT"}
    assert _resolve_team_id_from_payload(payload, event) == "T_TOP"


def test_resolve_team_id_from_payload_uses_authorizations_fallback():
    """Team ID should fallback to authorizations[0].team_id for event payloads."""
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src.worker import _resolve_team_id_from_payload

    payload = {"authorizations": [{"team_id": "T_AUTH"}]}
    event = {}
    assert _resolve_team_id_from_payload(payload, event) == "T_AUTH"


def test_handle_message_event_channel_join_falls_back_workspace_by_channel():
    """Channel join should still send fallback message when team_id is unavailable."""
    import asyncio
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src import worker

    captured = {"sent": 0}

    async def _fake_get_workspace_by_team(_env, _team_id):
        return None

    async def _fake_get_workspace_by_channel_id(_env, _channel_id):
        return {
            "id": 7,
            "team_id": "T070JPE5BQQ",
            "team_name": "Test WS",
            "access_token": "xoxb-token",
        }

    async def _fake_get_channel_name(_env, _workspace_id, _channel_id):
        return "contribute"

    async def _fake_get_bot_user_id(_env):
        return "UBOT"

    async def _fake_get_channel_by_slack_id(_env, _workspace_id, _channel_id):
        return None

    def _fake_get_channel_join_message(_team_id, _channel_id):
        return "Welcome <@{user_id}>"

    async def _fake_send_ephemeral(
        _env,
        _channel,
        _user,
        _text,
        blocks=None,
        token=None,
        branding_tracking_id="",
    ):
        captured["sent"] += 1
        captured["text"] = _text
        return {"ok": True}

    async def _fake_db_log_event(*_args, **_kwargs):
        return True

    orig_get_ws_by_team = worker.db_get_workspace_by_team
    orig_get_ws_by_channel = worker.db_get_workspace_by_channel_id
    orig_get_channel_name = worker.db_get_channel_name
    orig_get_bot_user_id = worker.get_bot_user_id
    orig_get_channel_row = worker.db_get_channel_by_slack_id
    orig_get_join_msg = worker.get_channel_join_message
    orig_send_ephemeral = worker.send_slack_ephemeral_message
    orig_log_event = worker.db_log_event

    worker.db_get_workspace_by_team = _fake_get_workspace_by_team
    worker.db_get_workspace_by_channel_id = _fake_get_workspace_by_channel_id
    worker.db_get_channel_name = _fake_get_channel_name
    worker.get_bot_user_id = _fake_get_bot_user_id
    worker.db_get_channel_by_slack_id = _fake_get_channel_by_slack_id
    worker.get_channel_join_message = _fake_get_channel_join_message
    worker.send_slack_ephemeral_message = _fake_send_ephemeral
    worker.db_log_event = _fake_db_log_event

    try:
        env = Mock()
        event = {
            "subtype": "channel_join",
            "user": "U123",
            "channel": "C077QBBLY1Z",
            "channel_type": "channel",
            "text": "",
        }
        result = asyncio.run(worker.handle_message_event(env, event, team_id=""))
    finally:
        worker.db_get_workspace_by_team = orig_get_ws_by_team
        worker.db_get_workspace_by_channel_id = orig_get_ws_by_channel
        worker.db_get_channel_name = orig_get_channel_name
        worker.get_bot_user_id = orig_get_bot_user_id
        worker.db_get_channel_by_slack_id = orig_get_channel_row
        worker.get_channel_join_message = orig_get_join_msg
        worker.send_slack_ephemeral_message = orig_send_ephemeral
        worker.db_log_event = orig_log_event

    assert result.get("ok") is True
    assert result.get("action") == "channel_join_logged"
    assert captured["sent"] == 1
    assert "<@U123>" in captured["text"]


def test_handle_message_event_channel_join_fallback_to_dm_when_ephemeral_fails():
    """When channel ephemeral send fails, join message should fallback to DM."""
    import asyncio
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src import worker

    captured = {"ephemeral": 0, "dm": 0}

    async def _fake_get_workspace_by_team(_env, _team_id):
        return {
            "id": 7,
            "team_id": "T070JPE5BQQ",
            "team_name": "Test WS",
            "access_token": "xoxb-token",
        }

    async def _fake_get_channel_name(_env, _workspace_id, _channel_id):
        return "contribute"

    async def _fake_get_bot_user_id(_env):
        return "UBOT"

    async def _fake_get_channel_by_slack_id(_env, _workspace_id, _channel_id):
        return None

    def _fake_get_channel_join_message(_team_id, _channel_id):
        return "Welcome <@{user_id}>"

    async def _fake_send_ephemeral(
        _env,
        _channel,
        _user,
        _text,
        blocks=None,
        token=None,
        branding_tracking_id="",
    ):
        captured["ephemeral"] += 1
        return {"ok": False, "error": "not_in_channel"}

    async def _fake_open_conversation(_env, _user, token=None):
        return {"ok": True, "channel": {"id": "D123"}}

    async def _fake_send_message(
        _env,
        _channel,
        _text,
        blocks=None,
        token=None,
        include_branding=True,
        branding_tracking_id="",
    ):
        captured["dm"] += 1
        captured["dm_text"] = _text
        return {"ok": True}

    async def _fake_db_log_event(*_args, **_kwargs):
        return True

    orig_get_ws_by_team = worker.db_get_workspace_by_team
    orig_get_channel_name = worker.db_get_channel_name
    orig_get_bot_user_id = worker.get_bot_user_id
    orig_get_channel_row = worker.db_get_channel_by_slack_id
    orig_get_join_msg = worker.get_channel_join_message
    orig_send_ephemeral = worker.send_slack_ephemeral_message
    orig_open_conversation = worker.open_conversation
    orig_send_message = worker.send_slack_message
    orig_log_event = worker.db_log_event

    worker.db_get_workspace_by_team = _fake_get_workspace_by_team
    worker.db_get_channel_name = _fake_get_channel_name
    worker.get_bot_user_id = _fake_get_bot_user_id
    worker.db_get_channel_by_slack_id = _fake_get_channel_by_slack_id
    worker.get_channel_join_message = _fake_get_channel_join_message
    worker.send_slack_ephemeral_message = _fake_send_ephemeral
    worker.open_conversation = _fake_open_conversation
    worker.send_slack_message = _fake_send_message
    worker.db_log_event = _fake_db_log_event

    try:
        env = Mock()
        event = {
            "subtype": "channel_join",
            "user": "U123",
            "channel": "C077QBBLY1Z",
            "channel_type": "channel",
            "text": "",
        }
        result = asyncio.run(
            worker.handle_message_event(env, event, team_id="T070JPE5BQQ")
        )
    finally:
        worker.db_get_workspace_by_team = orig_get_ws_by_team
        worker.db_get_channel_name = orig_get_channel_name
        worker.get_bot_user_id = orig_get_bot_user_id
        worker.db_get_channel_by_slack_id = orig_get_channel_row
        worker.get_channel_join_message = orig_get_join_msg
        worker.send_slack_ephemeral_message = orig_send_ephemeral
        worker.open_conversation = orig_open_conversation
        worker.send_slack_message = orig_send_message
        worker.db_log_event = orig_log_event

    assert result.get("ok") is True
    assert result.get("action") == "channel_join_logged"
    assert captured["ephemeral"] == 1
    assert captured["dm"] == 1
    assert "<@U123>" in captured["dm_text"]


def test_webhook_channel_join_sequence_sends_message_once():
    """Webhook sequence (message + member_joined_channel) should send one join message."""
    import asyncio
    import json
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src import worker

    captured = {"ephemeral": 0, "text": ""}

    class _FakeRequest:
        def __init__(self, payload):
            self.method = "POST"
            self.url = "https://lettuce.owaspblt.org/webhook"
            self.headers = {
                "Content-Type": "application/json",
                "X-Slack-Request-Timestamp": "1774214999",
                "X-Slack-Signature": "v0=fake",
            }
            self._body = json.dumps(payload)

        async def text(self):
            return self._body

    async def _fake_db_get_workspace_by_team(_env, _team_id):
        return {
            "id": 6,
            "team_id": "T070JPE5BQQ",
            "team_name": "Test WS",
            "access_token": "xoxb-token",
        }

    async def _fake_db_get_workspace_by_channel_id(_env, _channel_id):
        return {
            "id": 6,
            "team_id": "T070JPE5BQQ",
            "team_name": "Test WS",
            "access_token": "xoxb-token",
        }

    async def _fake_db_get_channel_name(_env, _workspace_id, _channel_id):
        return "general"

    async def _fake_get_bot_user_id(_env):
        return "UBOT"

    async def _fake_db_get_channel_by_slack_id(_env, _workspace_id, _channel_id):
        return None

    async def _fake_get_channel_join_message_runtime(_env, _team_id, _channel_id):
        return "Welcome <@{user_id}>"

    async def _fake_send_ephemeral(
        _env,
        _channel,
        _user,
        _text,
        blocks=None,
        token=None,
        branding_tracking_id="",
    ):
        captured["ephemeral"] += 1
        captured["text"] = _text
        return {"ok": True}

    async def _fake_db_log_event(*_args, **_kwargs):
        return True

    orig_verify = worker.verify_slack_signature
    orig_get_ws_by_team = worker.db_get_workspace_by_team
    orig_get_ws_by_channel = worker.db_get_workspace_by_channel_id
    orig_get_channel_name = worker.db_get_channel_name
    orig_get_bot_user_id = worker.get_bot_user_id
    orig_get_channel_row = worker.db_get_channel_by_slack_id
    orig_get_join_msg_runtime = worker.get_channel_join_message_runtime
    orig_send_ephemeral = worker.send_slack_ephemeral_message
    orig_log_event = worker.db_log_event

    worker.verify_slack_signature = lambda *_args, **_kwargs: True
    worker.db_get_workspace_by_team = _fake_db_get_workspace_by_team
    worker.db_get_workspace_by_channel_id = _fake_db_get_workspace_by_channel_id
    worker.db_get_channel_name = _fake_db_get_channel_name
    worker.get_bot_user_id = _fake_get_bot_user_id
    worker.db_get_channel_by_slack_id = _fake_db_get_channel_by_slack_id
    worker.get_channel_join_message_runtime = _fake_get_channel_join_message_runtime
    worker.send_slack_ephemeral_message = _fake_send_ephemeral
    worker.db_log_event = _fake_db_log_event

    try:
        env = Mock()

        message_payload = {
            "type": "event_callback",
            "team_id": "T070JPE5BQQ",
            "event": {
                "type": "message",
                "subtype": "channel_join",
                "user": "U06V72UT0J1",
                "channel": "C077QBBLY1Z",
                "channel_type": "channel",
                "text": "",
            },
        }
        member_joined_payload = {
            "type": "event_callback",
            "team_id": "T070JPE5BQQ",
            "event": {
                "type": "member_joined_channel",
                "user": "U06V72UT0J1",
                "channel": "C077QBBLY1Z",
                "channel_type": "C",
            },
        }

        asyncio.run(worker.handle_request(_FakeRequest(message_payload), env))
        asyncio.run(worker.handle_request(_FakeRequest(member_joined_payload), env))
    finally:
        worker.verify_slack_signature = orig_verify
        worker.db_get_workspace_by_team = orig_get_ws_by_team
        worker.db_get_workspace_by_channel_id = orig_get_ws_by_channel
        worker.db_get_channel_name = orig_get_channel_name
        worker.get_bot_user_id = orig_get_bot_user_id
        worker.db_get_channel_by_slack_id = orig_get_channel_row
        worker.get_channel_join_message_runtime = orig_get_join_msg_runtime
        worker.send_slack_ephemeral_message = orig_send_ephemeral
        worker.db_log_event = orig_log_event

    assert captured["ephemeral"] == 1
    assert "<@U06V72UT0J1>" in captured["text"]


def test_handle_team_join_logs_logo_tracking_for_verification():
    """Team join DM should persist logo_tracking_id so /logo-hit can verify it."""
    import asyncio
    import json
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src import worker

    captured = {"send_tracking_id": "", "log_kwargs": {}}

    async def _fake_get_bot_user_id(_env):
        return "UBOT"

    async def _fake_db_get_workspace_by_team(_env, _team_id):
        return {"id": 8, "team_id": "T070JPE5BQQ", "access_token": "xoxb-token"}

    async def _fake_open_conversation(_env, _user_id, token=None):
        return {"ok": True, "channel": {"id": "D123TEAM"}}

    async def _fake_db_get_channels(_env, _workspace_id):
        return []

    async def _fake_send_slack_message(
        _env,
        _channel,
        _text,
        blocks=None,
        token=None,
        include_branding=True,
        branding_tracking_id="",
    ):
        captured["send_tracking_id"] = branding_tracking_id
        return {"ok": True}

    async def _fake_db_log_event(*_args, **kwargs):
        captured["log_kwargs"] = kwargs
        return True

    orig_get_bot_user_id = worker.get_bot_user_id
    orig_get_workspace_by_team = worker.db_get_workspace_by_team
    orig_open_conversation = worker.open_conversation
    orig_get_channels = worker.db_get_channels
    orig_send_message = worker.send_slack_message
    orig_log_event = worker.db_log_event

    worker.get_bot_user_id = _fake_get_bot_user_id
    worker.db_get_workspace_by_team = _fake_db_get_workspace_by_team
    worker.open_conversation = _fake_open_conversation
    worker.db_get_channels = _fake_db_get_channels
    worker.send_slack_message = _fake_send_slack_message
    worker.db_log_event = _fake_db_log_event

    try:
        env = Mock()
        event = {"user": {"id": "UJOIN"}}
        result = asyncio.run(worker.handle_team_join(env, event, team_id="T070JPE5BQQ"))
    finally:
        worker.get_bot_user_id = orig_get_bot_user_id
        worker.db_get_workspace_by_team = orig_get_workspace_by_team
        worker.open_conversation = orig_open_conversation
        worker.db_get_channels = orig_get_channels
        worker.send_slack_message = orig_send_message
        worker.db_log_event = orig_log_event

    assert result.get("ok") is True
    assert captured["send_tracking_id"]
    request_data = json.loads(captured["log_kwargs"]["request_data"])
    assert request_data["logo_tracking_id"] == captured["send_tracking_id"]
    assert request_data["dm_channel"] == "D123TEAM"


def test_db_mark_join_message_verified_by_tracking_accepts_team_join():
    """Verification lookup should include Team_Join events in addition to channel join messages."""
    import asyncio
    import json
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src import worker

    state = {"select_sql": "", "updated_payload": {}}

    class _FakeStmt:
        def __init__(self, sql):
            self.sql = sql
            self.args = ()

        def bind(self, *args):
            self.args = args
            return self

        async def first(self):
            state["select_sql"] = self.sql
            return {
                "id": 101,
                "request_data": '{"logo_tracking_id": "tid-team", "kind": "team_join"}',
            }

        async def run(self):
            payload = json.loads(self.args[0])
            state["updated_payload"] = payload
            return {"ok": True}

    class _FakeDB:
        def prepare(self, sql):
            return _FakeStmt(sql)

    env = Mock()
    env.DB = _FakeDB()

    ok = asyncio.run(
        worker.db_mark_join_message_verified_by_tracking(
            env,
            "tid-team",
            "203.0.113.10",
            "pytest-agent",
        )
    )

    assert ok is True
    assert "Team_Join" in state["select_sql"]
    assert state["updated_payload"]["verification_ip"] == "203.0.113.10"
    assert state["updated_payload"]["verification_user_agent"] == "pytest-agent"
    assert state["updated_payload"].get("verified_at")


def test_handle_team_join_duplicate_event_id_is_skipped():
    """Duplicate Team Join event_id should skip welcome send and avoid Team_Join recount."""
    import asyncio
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src import worker

    captured = {"send_calls": 0, "log_events": []}

    async def _fake_get_bot_user_id(_env):
        return "UBOT"

    async def _fake_db_get_workspace_by_team(_env, _team_id):
        return {"id": 8, "team_id": "T070JPE5BQQ", "access_token": "xoxb-token"}

    async def _fake_db_has_team_join_event_id(_env, _workspace_id, _event_id):
        return True

    async def _fake_send_slack_message(*_args, **_kwargs):
        captured["send_calls"] += 1
        return {"ok": True}

    async def _fake_db_log_event(_env, _workspace_id, event_type, *_args, **_kwargs):
        captured["log_events"].append(event_type)
        return True

    orig_get_bot_user_id = worker.get_bot_user_id
    orig_get_workspace = worker.db_get_workspace_by_team
    orig_has_duplicate = worker.db_has_team_join_event_id
    orig_send_message = worker.send_slack_message
    orig_db_log_event = worker.db_log_event

    worker.get_bot_user_id = _fake_get_bot_user_id
    worker.db_get_workspace_by_team = _fake_db_get_workspace_by_team
    worker.db_has_team_join_event_id = _fake_db_has_team_join_event_id
    worker.send_slack_message = _fake_send_slack_message
    worker.db_log_event = _fake_db_log_event

    try:
        env = Mock()
        event = {
            "user": {"id": "UJOIN"},
            "_event_id": "EvDuplicate123",
            "_event_time": 1774219000,
            "_retry_num": "1",
            "_retry_reason": "http_timeout",
        }
        result = asyncio.run(worker.handle_team_join(env, event, team_id="T070JPE5BQQ"))
    finally:
        worker.get_bot_user_id = orig_get_bot_user_id
        worker.db_get_workspace_by_team = orig_get_workspace
        worker.db_has_team_join_event_id = orig_has_duplicate
        worker.send_slack_message = orig_send_message
        worker.db_log_event = orig_db_log_event

    assert result.get("ok") is True
    assert "Duplicate" in str(result.get("message") or "")
    assert captured["send_calls"] == 0
    assert "Team_Join_Duplicate" in captured["log_events"]
    assert "Team_Join" not in captured["log_events"]


def test_webhook_persists_webhook_received_event_with_request_data():
    """Webhook handler should persist full inbound payload metadata into events table."""
    import asyncio
    import json
    import sys
    from unittest.mock import Mock

    sys.modules["js"] = Mock()
    sys.modules["cloudflare"] = Mock()
    sys.modules["workers"] = Mock()

    from src import worker

    captured = {"event_types": [], "request_data": {}, "webhook_fields": {}}

    class _FakeRequest:
        def __init__(self, payload):
            self.method = "POST"
            self.url = "https://lettuce.owaspblt.org/webhook"
            self.headers = {
                "Content-Type": "application/json",
                "X-Slack-Request-Timestamp": "1774219999",
                "X-Slack-Signature": "v0=fake",
                "X-Slack-Retry-Num": "1",
                "X-Slack-Retry-Reason": "http_timeout",
            }
            self._body = json.dumps(payload)

        async def text(self):
            return self._body

    async def _fake_db_get_workspace_by_team(_env, _team_id):
        return {"id": 6, "team_id": "T070JPE5BQQ", "access_token": "xoxb-token"}

    async def _fake_handle_message_event(_env, _event, team_id=None):
        return {"ok": True, "team_id": team_id}

    async def _fake_db_log_event(_env, _workspace_id, event_type, *_args, **kwargs):
        captured["event_types"].append(event_type)
        if event_type == "Webhook_Received":
            captured["request_data"] = json.loads(kwargs.get("request_data") or "{}")
            captured["webhook_fields"] = {
                "webhook_body_type": kwargs.get("webhook_body_type"),
                "webhook_event_id": kwargs.get("webhook_event_id"),
                "webhook_event_time": kwargs.get("webhook_event_time"),
                "webhook_event_subtype": kwargs.get("webhook_event_subtype"),
                "webhook_retry_num": kwargs.get("webhook_retry_num"),
                "webhook_retry_reason": kwargs.get("webhook_retry_reason"),
            }
        return True

    orig_verify = worker.verify_slack_signature
    orig_get_workspace = worker.db_get_workspace_by_team
    orig_handle_message_event = worker.handle_message_event
    orig_db_log_event = worker.db_log_event

    worker.verify_slack_signature = lambda *_args, **_kwargs: True
    worker.db_get_workspace_by_team = _fake_db_get_workspace_by_team
    worker.handle_message_event = _fake_handle_message_event
    worker.db_log_event = _fake_db_log_event

    try:
        env = Mock()
        payload = {
            "type": "event_callback",
            "team_id": "T070JPE5BQQ",
            "event_id": "EvWebhookPersist1",
            "event_time": 1774219999,
            "event": {
                "type": "message",
                "subtype": "channel_join",
                "user": "U123",
                "channel": "C123",
                "channel_type": "channel",
            },
        }
        asyncio.run(worker.handle_request(_FakeRequest(payload), env))
    finally:
        worker.verify_slack_signature = orig_verify
        worker.db_get_workspace_by_team = orig_get_workspace
        worker.handle_message_event = orig_handle_message_event
        worker.db_log_event = orig_db_log_event

    assert "Webhook_Received" in captured["event_types"]
    assert captured["request_data"].get("event_id") == "EvWebhookPersist1"
    assert captured["request_data"].get("event_type") == "message"
    assert captured["request_data"].get("event_subtype") == "channel_join"
    assert captured["request_data"].get("retry_num") == "1"
    assert captured["request_data"].get("raw_body")
    assert isinstance(captured["request_data"].get("parsed_body"), dict)
    assert captured["webhook_fields"]["webhook_body_type"] == "event_callback"
    assert captured["webhook_fields"]["webhook_event_id"] == "EvWebhookPersist1"
    assert str(captured["webhook_fields"]["webhook_event_time"]) == "1774219999"
    assert captured["webhook_fields"]["webhook_event_subtype"] == "channel_join"
    assert captured["webhook_fields"]["webhook_retry_num"] == "1"
    assert captured["webhook_fields"]["webhook_retry_reason"] == "http_timeout"
