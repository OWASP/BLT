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
    assert "Welcome to the OWASP Slack Community" in message


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
