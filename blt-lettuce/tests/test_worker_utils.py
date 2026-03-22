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
