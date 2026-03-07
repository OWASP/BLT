"""Tests for worker utility functions."""
import pytest
from unittest.mock import MagicMock


def test_verify_oauth_state_valid():
    """Test OAuth state verification with valid state."""
    # Import inline to avoid Cloudflare runtime dependencies
    import sys
    from unittest.mock import Mock
    
    # Mock the worker module
    sys.modules['js'] = Mock()
    sys.modules['cloudflare'] = Mock()
    sys.modules['workers'] = Mock()
    
    from src.worker import _verify_oauth_state
    
    state = "signin:abc123"
    result = _verify_oauth_state(state, state)
    
    assert result == "signin"


def test_verify_oauth_state_invalid():
    """Test OAuth state verification with invalid state."""
    import sys
    from unittest.mock import Mock
    
    sys.modules['js'] = Mock()
    sys.modules['cloudflare'] = Mock()
    sys.modules['workers'] = Mock()
    
    from src.worker import _verify_oauth_state
    
    stored = "signin:abc123"
    received = "signin:xyz789"
    result = _verify_oauth_state(stored, received)
    
    assert result is None


def test_verify_oauth_state_missing():
    """Test OAuth state verification with missing states."""
    import sys
    from unittest.mock import Mock
    
    sys.modules['js'] = Mock()
    sys.modules['cloudflare'] = Mock()
    sys.modules['workers'] = Mock()
    
    from src.worker import _verify_oauth_state
    
    result = _verify_oauth_state("", "signin:abc123")
    assert result is None
    
    result = _verify_oauth_state("signin:abc123", "")
    assert result is None


def test_get_utc_now():
    """Test UTC timestamp generation."""
    import sys
    from unittest.mock import Mock
    
    sys.modules['js'] = Mock()
    sys.modules['cloudflare'] = Mock()
    sys.modules['workers'] = Mock()
    
    from src.worker import get_utc_now
    
    timestamp = get_utc_now()
    
    assert isinstance(timestamp, str)
    assert "T" in timestamp
    assert timestamp.endswith("+00:00") or timestamp.endswith("Z")


def test_parse_cookies():
    """Test cookie parsing from headers."""
    import sys
    from unittest.mock import Mock
    
    sys.modules['js'] = Mock()
    sys.modules['cloudflare'] = Mock()
    sys.modules['workers'] = Mock()
    
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
    
    sys.modules['js'] = Mock()
    sys.modules['cloudflare'] = Mock()
    sys.modules['workers'] = Mock()
    
    from src.worker import parse_cookies
    
    request = Mock()
    request.headers = {}
    
    cookies = parse_cookies(request)
    
    assert cookies == {}


def test_is_valid_slack_url():
    """Test Slack URL validation."""
    import sys
    from unittest.mock import Mock
    
    sys.modules['js'] = Mock()
    sys.modules['cloudflare'] = Mock()
    sys.modules['workers'] = Mock()
    
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
    
    sys.modules['js'] = Mock()
    sys.modules['cloudflare'] = Mock()
    sys.modules['workers'] = Mock()
    
    from src.worker import WELCOME_MESSAGE
    
    user_id = "U12345"
    message = WELCOME_MESSAGE.format(user_id=user_id)
    
    assert "<@U12345>" in message
    assert "Welcome to the OWASP Slack Community" in message
