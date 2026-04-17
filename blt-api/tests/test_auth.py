"""
Tests for the auth handler (src/handlers/auth.py).

Covers handle_signin with focus on the is_active check (issue #55)
and basic validation paths for signup and verify-email.
"""

import sys
import json
import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# Mock workers and external modules before importing handlers
_mock_workers = MagicMock()


class _MockResponse:
    def __init__(self, data, status=200):
        self.data = data
        self.status = status
        self.body = json.dumps(data)

    @classmethod
    def json(cls, data, status=200, **kwargs):
        return cls(data, status)


_mock_workers.Response = _MockResponse
sys.modules["workers"] = _mock_workers

# Removed sys.modules.js mock to allow utils.py fallback


from handlers.auth import handle_signin, handle_signup, handle_verify_email, SIGNUP_RATE_LIMIT, SIGNIN_RATE_LIMIT  # noqa: E402


@pytest.fixture(autouse=True)
def mock_response():
    """Ensure handle_auth uses the local _MockResponse class."""
    with patch("handlers.auth.Response", _MockResponse):
        yield


HASHING_ITERATIONS = 1


def _hash_password(password, salt="abcdef1234567890abcdef1234567890"):
    """Create a hashed password in the same format as the signup handler."""
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), HASHING_ITERATIONS
    )
    return f"{salt}${pw_hash.hex()}"


class MockRequest:
    def __init__(self, method="POST", body=None):
        self.method = method
        self._body = body

    async def text(self):
        if self._body is None:
            return ""
        if isinstance(self._body, dict):
            return json.dumps(self._body)
        return str(self._body)


class MockEnv:
    JWT_SECRET = "test-secret-key"
    BLT_API_BASE_URL = "http://localhost:8787"
    MAILGUN_API_KEY = "test-key"
    MAILGUN_DOMAIN = "test.mailgun.org"
    SENDGRID_USERNAME = "test-sendgrid-user"
    SENDGRID_PASSWORD = "test-sendgrid-pass"
    FROM_EMAIL = "noreply@example.com"


@pytest.fixture(autouse=True)
def reset_rate_limits():
    SIGNUP_RATE_LIMIT.clear()
    SIGNIN_RATE_LIMIT.clear()
    yield
    SIGNUP_RATE_LIMIT.clear()
    SIGNIN_RATE_LIMIT.clear()


def _make_mock_user(is_active=True, password="testpass123456"):
    """Create a mock user dict as returned by User.objects().filter().first()."""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "password": _hash_password(password),
        "is_active": is_active,
    }


# ─── handle_signin tests ───────────────────────────────────────────────


class TestSigninIsActiveCheck:
    """Tests for issue #55: signin must reject inactive (unverified) users."""

    @pytest.mark.asyncio
    async def test_inactive_user_gets_403(self):
        """Unverified user with correct password should get 403, not a token."""
        user = _make_mock_user(is_active=False)
        mock_user_cls = MagicMock()
        mock_qs = MagicMock()
        mock_qs.filter.return_value = mock_qs
        mock_qs.first = AsyncMock(return_value=user)
        mock_user_cls.objects.return_value = mock_qs

        body = {"username": "testuser", "password": "testpass123456"}
        request = MockRequest(method="POST", body=body)

        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())), \
             patch("handlers.auth.User", mock_user_cls), \
             patch("handlers.auth.__HASHING_ITERATIONS", HASHING_ITERATIONS):
            resp = await handle_signin(request, MockEnv(), {}, {}, "/auth/signin")

        assert resp.status == 403
        data = resp.data if hasattr(resp, 'data') else json.loads(resp.body)
        assert "not verified" in data.get("message", "").lower()

    @pytest.mark.asyncio
    async def test_active_user_gets_token(self):
        """Verified user with correct password should get 200 + token."""
        user = _make_mock_user(is_active=True)
        mock_user_cls = MagicMock()
        mock_qs = MagicMock()
        mock_qs.filter.return_value = mock_qs
        mock_qs.first = AsyncMock(return_value=user)
        mock_user_cls.objects.return_value = mock_qs

        body = {"username": "testuser", "password": "testpass123456"}
        request = MockRequest(method="POST", body=body)

        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())), \
             patch("handlers.auth.User", mock_user_cls), \
             patch("handlers.auth.__HASHING_ITERATIONS", HASHING_ITERATIONS), \
             patch("handlers.auth.create_access_token", return_value="fake.jwt.token"):
            resp = await handle_signin(request, MockEnv(), {}, {}, "/auth/signin")

        assert resp.status == 200
        data = resp.data if isinstance(resp.data, dict) else json.loads(resp.body)
        assert "token" in data

    @pytest.mark.asyncio
    async def test_is_active_zero_treated_as_inactive(self):
        """D1/SQLite stores booleans as 0/1. is_active=0 should be rejected."""
        user = _make_mock_user(is_active=0)
        mock_user_cls = MagicMock()
        mock_qs = MagicMock()
        mock_qs.filter.return_value = mock_qs
        mock_qs.first = AsyncMock(return_value=user)
        mock_user_cls.objects.return_value = mock_qs

        body = {"username": "testuser", "password": "testpass123456"}
        request = MockRequest(method="POST", body=body)

        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())), \
             patch("handlers.auth.User", mock_user_cls), \
             patch("handlers.auth.__HASHING_ITERATIONS", HASHING_ITERATIONS):
            resp = await handle_signin(request, MockEnv(), {}, {}, "/auth/signin")

        assert resp.status == 403


class TestSigninValidation:
    """Basic validation tests for handle_signin."""

    @pytest.mark.asyncio
    async def test_wrong_method_returns_error(self):
        request = MockRequest(method="GET", body=None)
        resp = await handle_signin(request, MockEnv(), {}, {}, "/auth/signin")
        assert resp.status in (404, 405)

    @pytest.mark.asyncio
    async def test_empty_body_returns_400(self):
        request = MockRequest(method="POST", body=None)
        resp = await handle_signin(request, MockEnv(), {}, {}, "/auth/signin")
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_missing_password_returns_400(self):
        request = MockRequest(method="POST", body={"username": "testuser"})
        with patch("handlers.auth.check_required_fields", AsyncMock(return_value=(False, "password"))):
            resp = await handle_signin(request, MockEnv(), {}, {}, "/auth/signin")
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_nonexistent_user_returns_401(self):
        mock_user_cls = MagicMock()
        mock_qs = MagicMock()
        mock_qs.filter.return_value = mock_qs
        mock_qs.first = AsyncMock(return_value=None)
        mock_user_cls.objects.return_value = mock_qs

        body = {"username": "nouser", "password": "testpass123456"}
        request = MockRequest(method="POST", body=body)

        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())), \
             patch("handlers.auth.User", mock_user_cls):
            resp = await handle_signin(request, MockEnv(), {}, {}, "/auth/signin")

        assert resp.status == 401

    @pytest.mark.asyncio
    async def test_wrong_password_returns_401(self):
        user = _make_mock_user(is_active=True, password="correctpassword123")
        mock_user_cls = MagicMock()
        mock_qs = MagicMock()
        mock_qs.filter.return_value = mock_qs
        mock_qs.first = AsyncMock(return_value=user)
        mock_user_cls.objects.return_value = mock_qs

        body = {"username": "testuser", "password": "wrongpassword123"}
        request = MockRequest(method="POST", body=body)

        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())), \
             patch("handlers.auth.User", mock_user_cls), \
             patch("handlers.auth.__HASHING_ITERATIONS", HASHING_ITERATIONS):
            resp = await handle_signin(request, MockEnv(), {}, {}, "/auth/signin")

        assert resp.status == 401

    @pytest.mark.asyncio
    async def test_db_connection_error_returns_500(self):
        body = {"username": "testuser", "password": "testpass123456"}
        request = MockRequest(method="POST", body=body)

        with patch("handlers.auth.get_db_safe", AsyncMock(side_effect=Exception("DB down"))):
            resp = await handle_signin(request, MockEnv(), {}, {}, "/auth/signin")

        assert resp.status == 500

    @pytest.mark.asyncio
    async def test_signin_is_rate_limited_after_burst(self):
        user = _make_mock_user(is_active=True)
        mock_user_cls = MagicMock()
        mock_qs = MagicMock()
        mock_qs.filter.return_value = mock_qs
        mock_qs.first = AsyncMock(return_value=user)
        mock_user_cls.objects.return_value = mock_qs

        body = {"username": "testuser", "password": "testpass123456"}
        request = MockRequest(method="POST", body=body)

        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())), \
             patch("handlers.auth.User", mock_user_cls), \
             patch("handlers.auth.__HASHING_ITERATIONS", HASHING_ITERATIONS), \
             patch("handlers.auth.create_access_token", return_value="fake.jwt.token"):
            first = await handle_signin(request, MockEnv(), {}, {}, "/auth/signin")
            second = await handle_signin(request, MockEnv(), {}, {}, "/auth/signin")
            third = await handle_signin(request, MockEnv(), {}, {}, "/auth/signin")

        assert first.status == 200
        assert second.status == 200
        assert third.status == 429


# ─── handle_signup tests ────────────────────────────────────────────────


class TestSignupValidation:
    """Basic validation tests for handle_signup."""

    @pytest.mark.asyncio
    async def test_wrong_method_returns_error(self):
        request = MockRequest(method="GET", body=None)
        resp = await handle_signup(request, MockEnv(), {}, {}, "/auth/signup")
        assert resp.status in (404, 405)

    @pytest.mark.asyncio
    async def test_empty_body_returns_400(self):
        request = MockRequest(method="POST", body=None)
        resp = await handle_signup(request, MockEnv(), {}, {}, "/auth/signup")
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_missing_field_returns_400(self):
        request = MockRequest(method="POST", body={"username": "user123", "password": "testpass123456"})
        with patch("handlers.auth.check_required_fields", AsyncMock(return_value=(False, "email"))):
            resp = await handle_signup(request, MockEnv(), {}, {}, "/auth/signup")
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_signup_is_rate_limited_after_burst(self):
        body = {"username": "user123", "password": "Testpass123456!", "email": "user@example.com"}
        request = MockRequest(method="POST", body=body)

        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())), \
             patch("handlers.auth.check_required_fields", AsyncMock(return_value=(True, None))), \
             patch("handlers.auth.blind_index", side_effect=lambda value, *_args, **_kwargs: f"{value}-hash"), \
             patch("handlers.auth.encrypt_sensitive", side_effect=lambda value, *_args, **_kwargs: value), \
             patch("handlers.auth.User") as mock_user_cls, \
             patch("handlers.auth.EmailService") as mock_email_service, \
             patch("handlers.auth.generate_jwt_token", return_value="fake.token"):
            mock_qs = MagicMock()
            mock_qs.filter.return_value = mock_qs
            mock_qs.first = AsyncMock(return_value=None)
            mock_qs.delete = AsyncMock()
            mock_user_cls.objects.return_value = mock_qs
            mock_user_cls.create = AsyncMock(return_value={"id": 1})
            email_instance = MagicMock()
            email_instance.send_verification_email = AsyncMock(return_value=(200, "ok"))
            mock_email_service.return_value = email_instance

            first = await handle_signup(request, MockEnv(), {}, {}, "/auth/signup")
            second = await handle_signup(request, MockEnv(), {}, {}, "/auth/signup")
            third = await handle_signup(request, MockEnv(), {}, {}, "/auth/signup")

        assert first.status == 201
        assert second.status == 201
        assert third.status == 429


# ─── handle_verify_email tests ──────────────────────────────────────────


class TestVerifyEmailValidation:
    """Basic validation tests for handle_verify_email."""

    @pytest.mark.asyncio
    async def test_wrong_method_returns_error(self):
        request = MockRequest(method="POST", body=None)
        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())):
            resp = await handle_verify_email(request, MockEnv(), {}, {}, "/auth/verify-email")
        assert resp.status in (404, 405)

    @pytest.mark.asyncio
    async def test_missing_token_returns_400(self):
        request = MockRequest(method="GET", body=None)
        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())):
            resp = await handle_verify_email(request, MockEnv(), {}, {}, "/auth/verify-email")
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_invalid_token_returns_400(self):
        request = MockRequest(method="GET", body=None)
        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())), \
             patch("handlers.auth.decode_jwt", return_value=None):
            resp = await handle_verify_email(
                request, MockEnv(), {}, {"token": "bad.token.here"}, "/auth/verify-email"
            )
        assert resp.status == 400
