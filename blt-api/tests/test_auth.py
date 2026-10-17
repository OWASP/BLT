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


import handlers.auth as auth_module  # noqa: E402
from handlers.auth import handle_signin, handle_signup, handle_verify_email, SIGNUP_RATE_LIMIT, SIGNIN_RATE_LIMIT  # noqa: E402
from libs.jwt_utils import encode_jwt  # noqa: E402


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
    def __init__(self, method="POST", body=None, url="https://api.example.com/api/auth/signup"):
        self.method = method
        self._body = body
        self.url = url

    async def text(self):
        if self._body is None:
            return ""
        if isinstance(self._body, dict):
            return json.dumps(self._body)
        return str(self._body)


class MockEnv:
    JWT_SECRET = "test-secret-key"
    BLT_API_BASE_URL = "http://localhost:8787"
    SENDGRID_USERNAME = "test-sendgrid-user"
    SENDGRID_PASSWORD = "test-sendgrid-pass"
    FROM_EMAIL = "noreply@example.com"


class MockEnvMissingSendGrid:
    JWT_SECRET = "test-secret-key"
    BLT_API_BASE_URL = "http://localhost:8787"


class MockEnvSendGridWithoutUsername:
    JWT_SECRET = "test-secret-key"
    BLT_API_BASE_URL = "http://localhost:8787"
    SENDGRID_PASSWORD = "test-sendgrid-pass"
    FROM_EMAIL = "noreply@example.com"


class MockEnvSendGridApiKey:
    JWT_SECRET = "test-secret-key"
    BLT_API_BASE_URL = "http://localhost:8787"
    SENDGRID_API_KEY = "test-sendgrid-api-key"
    FROM_EMAIL = "noreply@example.com"


class MockEnvLocalOtp:
    JWT_SECRET = "test-secret-key"
    BLT_API_BASE_URL = "http://localhost:8787"
    LOCAL_AUTH_OTP = "123456"


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


def _make_auth_request(method="GET", body=None, user_id=1):
    token = encode_jwt({"user_id": user_id}, MockEnv.JWT_SECRET)
    request = MockRequest(method=method, body=body)
    request.headers = {"Authorization": f"Bearer {token}"}
    return request


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
        """Verified user with correct password should get 200 + Bearer token payload."""
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
        assert data["access_token"] == "fake.jwt.token"
        assert data["token"] == "fake.jwt.token"
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] == 24 * 3600

    @pytest.mark.asyncio
    async def test_active_user_can_sign_in_with_email_identifier(self):
        """Verified user should be able to sign in with email instead of username."""
        user = _make_mock_user(is_active=True)
        mock_user_cls = MagicMock()
        mock_qs = MagicMock()
        mock_qs.filter.return_value = mock_qs
        mock_qs.first = AsyncMock(return_value=user)
        mock_user_cls.objects.return_value = mock_qs

        body = {"identifier": "test@example.com", "password": "testpass123456"}
        request = MockRequest(method="POST", body=body)

        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())), \
             patch("handlers.auth.User", mock_user_cls), \
             patch("handlers.auth.blind_index", return_value="email-hash"), \
             patch("handlers.auth.__HASHING_ITERATIONS", HASHING_ITERATIONS), \
             patch("handlers.auth.create_access_token", return_value="fake.jwt.token"):
            resp = await handle_signin(request, MockEnv(), {}, {}, "/auth/signin")

        assert resp.status == 200
        mock_qs.filter.assert_called_once_with(email_hash="email-hash")

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
    async def test_signin_is_rate_limited_after_burst(self, monkeypatch):
        monkeypatch.setattr("handlers.auth._SIGNIN_MAX_REQUESTS", 2)
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
    async def test_signup_creates_local_identity_and_sends_24_hour_verification(self):
        mock_user_cls = MagicMock()
        mock_user_qs = MagicMock()
        mock_user_qs.filter.return_value = mock_user_qs
        mock_user_qs.first = AsyncMock(return_value=None)
        mock_user_cls.objects.return_value = mock_user_qs
        mock_user_cls.create = AsyncMock(return_value={"id": 42})

        mock_identity_cls = MagicMock()
        mock_identity_cls.create = AsyncMock(return_value={"id": 100})

        mock_email_service = MagicMock()
        mock_email_service.send_verification_email = AsyncMock(return_value=(202, ""))
        mock_email_service_cls = MagicMock(return_value=mock_email_service)

        body = {
            "username": "user123",
            "email": "user123@example.com",
            "password": "Testpass123456!",
        }
        request = MockRequest(method="POST", body=body)

        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())), \
             patch("handlers.auth.User", mock_user_cls), \
             patch("handlers.auth.UserAuthIdentity", mock_identity_cls, create=True), \
             patch("handlers.auth.EmailService", mock_email_service_cls), \
             patch("handlers.auth.generate_jwt_token", return_value="verify.jwt.token") as mock_generate_token, \
             patch("handlers.auth.__HASHING_ITERATIONS", HASHING_ITERATIONS):
            resp = await handle_signup(request, MockEnv(), {}, {}, "/auth/signup")

        assert resp.status == 201
        mock_identity_cls.create.assert_awaited_once()
        identity_kwargs = mock_identity_cls.create.await_args.kwargs
        assert identity_kwargs["user_id"] == 42
        assert identity_kwargs["provider"] == "local"
        assert identity_kwargs["provider_user_id"] == "42"
        mock_generate_token.assert_called_once_with(42, MockEnv.JWT_SECRET, expires_in=24 * 3600)
        mock_email_service.send_verification_email.assert_awaited_once()
        assert mock_email_service.send_verification_email.await_args.kwargs["expires_hours"] == 24

    @pytest.mark.asyncio
    async def test_signup_email_failure_rolls_back_user_and_local_identity(self):
        mock_user_cls = MagicMock()
        mock_user_qs = MagicMock()
        mock_user_qs.filter.return_value = mock_user_qs
        mock_user_qs.first = AsyncMock(return_value=None)
        mock_user_qs.delete = AsyncMock()
        mock_user_cls.objects.return_value = mock_user_qs
        mock_user_cls.create = AsyncMock(return_value={"id": 42})

        mock_identity_cls = MagicMock()
        mock_identity_qs = MagicMock()
        mock_identity_qs.filter.return_value = mock_identity_qs
        mock_identity_qs.delete = AsyncMock()
        mock_identity_cls.objects.return_value = mock_identity_qs
        mock_identity_cls.create = AsyncMock(return_value={"id": 100})

        mock_email_service = MagicMock()
        mock_email_service.send_verification_email = AsyncMock(return_value=(500, "send failed"))
        mock_email_service_cls = MagicMock(return_value=mock_email_service)

        body = {
            "username": "user123",
            "email": "user123@example.com",
            "password": "Testpass123456!",
        }
        request = MockRequest(method="POST", body=body)

        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())), \
             patch("handlers.auth.User", mock_user_cls), \
             patch("handlers.auth.UserAuthIdentity", mock_identity_cls), \
             patch("handlers.auth.EmailService", mock_email_service_cls), \
             patch("handlers.auth.generate_jwt_token", return_value="verify.jwt.token"), \
             patch("handlers.auth.__HASHING_ITERATIONS", HASHING_ITERATIONS):
            resp = await handle_signup(request, MockEnv(), {}, {}, "/auth/signup")

        assert resp.status == 503
        mock_identity_qs.filter.assert_called_once_with(user_id=42, provider="local")
        mock_identity_qs.delete.assert_awaited_once()
        mock_user_qs.filter.assert_called_with(id=42)
        mock_user_qs.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_signup_missing_sendgrid_config_returns_503_without_creating_user(self):
        mock_user_cls = MagicMock()
        mock_user_qs = MagicMock()
        mock_user_qs.filter.return_value = mock_user_qs
        mock_user_qs.first = AsyncMock(return_value=None)
        mock_user_cls.objects.return_value = mock_user_qs
        mock_user_cls.create = AsyncMock(return_value={"id": 42})

        mock_identity_cls = MagicMock()
        mock_identity_cls.create = AsyncMock(return_value={"id": 100})

        body = {
            "username": "user123",
            "email": "user123@example.com",
            "password": "Testpass123456!",
        }
        request = MockRequest(method="POST", body=body)

        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())) as get_db_safe, \
             patch("handlers.auth.User", mock_user_cls), \
             patch("handlers.auth.UserAuthIdentity", mock_identity_cls), \
             patch("handlers.auth.blind_index", side_effect=lambda value, *_args, **_kwargs: f"{value}-hash"), \
             patch("handlers.auth.encrypt_sensitive", side_effect=lambda value, *_args, **_kwargs: value):
            resp = await handle_signup(request, MockEnvMissingSendGrid(), {}, {}, "/api/auth/signup")

        assert resp.status == 503
        data = resp.data if hasattr(resp, "data") else json.loads(resp.body)
        assert "Email service is not configured" in data["message"]
        get_db_safe.assert_not_awaited()
        mock_user_cls.create.assert_not_called()
        mock_identity_cls.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_signup_defaults_sendgrid_username_when_api_key_and_sender_are_configured(self):
        mock_user_cls = MagicMock()
        mock_user_qs = MagicMock()
        mock_user_qs.filter.return_value = mock_user_qs
        mock_user_qs.first = AsyncMock(return_value=None)
        mock_user_cls.objects.return_value = mock_user_qs
        mock_user_cls.create = AsyncMock(return_value={"id": 42})

        mock_identity_cls = MagicMock()
        mock_identity_cls.create = AsyncMock(return_value={"id": 100})

        mock_email_service = MagicMock()
        mock_email_service.send_verification_email = AsyncMock(return_value=(202, ""))
        mock_email_service_cls = MagicMock(return_value=mock_email_service)

        body = {
            "username": "user123",
            "email": "user123@example.com",
            "password": "Testpass123456!",
        }
        request = MockRequest(method="POST", body=body)

        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())), \
             patch("handlers.auth.User", mock_user_cls), \
             patch("handlers.auth.UserAuthIdentity", mock_identity_cls), \
             patch("handlers.auth.EmailService", mock_email_service_cls), \
             patch("handlers.auth.generate_jwt_token", return_value="verify.jwt.token"), \
             patch("handlers.auth.__HASHING_ITERATIONS", HASHING_ITERATIONS):
            resp = await handle_signup(request, MockEnvSendGridWithoutUsername(), {}, {}, "/api/auth/signup")

        assert resp.status == 201
        mock_email_service_cls.assert_called_once_with(
            smtp_username="apikey",
            smtp_password="test-sendgrid-pass",
            from_email="noreply@example.com",
            from_name="OWASP BLT",
        )

    @pytest.mark.asyncio
    async def test_signup_accepts_sendgrid_api_key_binding_name(self):
        mock_user_cls = MagicMock()
        mock_user_qs = MagicMock()
        mock_user_qs.filter.return_value = mock_user_qs
        mock_user_qs.first = AsyncMock(return_value=None)
        mock_user_cls.objects.return_value = mock_user_qs
        mock_user_cls.create = AsyncMock(return_value={"id": 42})

        mock_identity_cls = MagicMock()
        mock_identity_cls.create = AsyncMock(return_value={"id": 100})

        mock_email_service = MagicMock()
        mock_email_service.send_verification_email = AsyncMock(return_value=(202, ""))
        mock_email_service_cls = MagicMock(return_value=mock_email_service)

        body = {
            "username": "user123",
            "email": "user123@example.com",
            "password": "Testpass123456!",
        }
        request = MockRequest(method="POST", body=body)

        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())), \
             patch("handlers.auth.User", mock_user_cls), \
             patch("handlers.auth.UserAuthIdentity", mock_identity_cls), \
             patch("handlers.auth.EmailService", mock_email_service_cls), \
             patch("handlers.auth.generate_jwt_token", return_value="verify.jwt.token"), \
             patch("handlers.auth.__HASHING_ITERATIONS", HASHING_ITERATIONS):
            resp = await handle_signup(request, MockEnvSendGridApiKey(), {}, {}, "/api/auth/signup")

        assert resp.status == 201
        mock_email_service_cls.assert_called_once_with(
            smtp_username="apikey",
            smtp_password="test-sendgrid-api-key",
            from_email="noreply@example.com",
            from_name="OWASP BLT",
        )

    @pytest.mark.asyncio
    async def test_local_signup_without_dev_otp_creates_pending_user_and_skips_email(self):
        mock_user_cls = MagicMock()
        mock_user_qs = MagicMock()
        mock_user_qs.filter.return_value = mock_user_qs
        mock_user_qs.first = AsyncMock(return_value=None)
        mock_user_cls.objects.return_value = mock_user_qs
        mock_user_cls.create = AsyncMock(return_value={"id": 42})

        mock_identity_cls = MagicMock()
        mock_identity_cls.create = AsyncMock(return_value={"id": 100})

        body = {
            "username": "user123",
            "email": "user123@example.com",
            "password": "Testpass123456!",
        }
        request = MockRequest(
            method="POST",
            body=body,
            url="http://localhost:8788/api/auth/signup",
        )

        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())), \
             patch("handlers.auth.User", mock_user_cls), \
             patch("handlers.auth.UserAuthIdentity", mock_identity_cls), \
             patch("handlers.auth.EmailService") as mock_email_service_cls, \
             patch("handlers.auth.__HASHING_ITERATIONS", HASHING_ITERATIONS):
            resp = await handle_signup(request, MockEnvLocalOtp(), {}, {}, "/api/auth/signup")

        assert resp.status == 201
        user_kwargs = mock_user_cls.create.await_args.kwargs
        assert user_kwargs["is_active"] is False
        assert "email_verified_at" not in user_kwargs
        mock_identity_cls.create.assert_awaited_once()
        mock_email_service_cls.assert_not_called()
        data = resp.data if hasattr(resp, "data") else json.loads(resp.body)
        assert data["requires_local_verification"] is True
        assert data["email_verified"] is False

    @pytest.mark.asyncio
    async def test_local_signup_rejects_pre_submit_dev_otp_without_creating_user(self):
        mock_user_cls = MagicMock()
        mock_identity_cls = MagicMock()

        body = {
            "username": "user123",
            "email": "user123@example.com",
            "password": "Testpass123456!",
            "dev_otp": "wrong",
        }
        request = MockRequest(
            method="POST",
            body=body,
            url="http://127.0.0.1:8788/api/auth/signup",
        )

        with patch("handlers.auth.get_db_safe", AsyncMock()) as get_db_safe, \
             patch("handlers.auth.User", mock_user_cls), \
             patch("handlers.auth.UserAuthIdentity", mock_identity_cls):
            resp = await handle_signup(request, MockEnvLocalOtp(), {}, {}, "/api/auth/signup")

        assert resp.status == 400
        data = resp.data if hasattr(resp, "data") else json.loads(resp.body)
        assert data["message"] == "Local verification code must be submitted after account creation"
        get_db_safe.assert_not_awaited()
        mock_user_cls.create.assert_not_called()
        mock_identity_cls.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_local_verify_with_dev_otp_activates_pending_user(self):
        mock_user_cls = MagicMock()
        mock_user_qs = MagicMock()
        mock_user_qs.filter.return_value = mock_user_qs
        mock_user_qs.first = AsyncMock(return_value={"id": 42, "is_active": False})
        mock_user_qs.update = AsyncMock(return_value=1)
        mock_user_cls.objects.return_value = mock_user_qs

        body = {"identifier": "user123", "dev_otp": "123456"}
        request = MockRequest(
            method="POST",
            body=body,
            url="http://localhost:8788/api/auth/verify-local",
        )

        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())), \
             patch("handlers.auth.User", mock_user_cls), \
             patch("handlers.auth.blind_index", return_value="user123-hash"):
            resp = await auth_module.handle_verify_local(request, MockEnvLocalOtp(), {}, {}, "/api/auth/verify-local")

        assert resp.status == 200
        mock_user_qs.filter.assert_called_once_with(username_hash="user123-hash")
        update_kwargs = mock_user_qs.update.await_args.kwargs
        assert update_kwargs["is_active"] is True
        assert update_kwargs["email_verified_at"]
        data = resp.data if hasattr(resp, "data") else json.loads(resp.body)
        assert data["email_verified"] is True

    @pytest.mark.asyncio
    async def test_local_verify_wrong_dev_otp_returns_400_without_db(self):
        body = {"identifier": "user123", "dev_otp": "wrong"}
        request = MockRequest(
            method="POST",
            body=body,
            url="http://localhost:8788/api/auth/verify-local",
        )

        with patch("handlers.auth.get_db_safe", AsyncMock()) as get_db_safe:
            resp = await auth_module.handle_verify_local(request, MockEnvLocalOtp(), {}, {}, "/api/auth/verify-local")

        assert resp.status == 400
        data = resp.data if hasattr(resp, "data") else json.loads(resp.body)
        assert data["message"] == "Invalid local verification code"
        get_db_safe.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_local_verify_rejects_production_requests_without_db(self):
        body = {"identifier": "user123", "dev_otp": "123456"}
        request = MockRequest(
            method="POST",
            body=body,
            url="https://api.example.com/api/auth/verify-local",
        )

        with patch("handlers.auth.get_db_safe", AsyncMock()) as get_db_safe:
            resp = await auth_module.handle_verify_local(request, MockEnvLocalOtp(), {}, {}, "/api/auth/verify-local")

        assert resp.status == 400
        data = resp.data if hasattr(resp, "data") else json.loads(resp.body)
        assert data["message"] == "Local verification is only available in local development"
        get_db_safe.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_production_signup_rejects_dev_otp_without_creating_user(self):
        mock_user_cls = MagicMock()
        mock_identity_cls = MagicMock()

        body = {
            "username": "user123",
            "email": "user123@example.com",
            "password": "Testpass123456!",
            "dev_otp": "123456",
        }
        request = MockRequest(
            method="POST",
            body=body,
            url="https://api.example.com/api/auth/signup",
        )

        with patch("handlers.auth.get_db_safe", AsyncMock()) as get_db_safe, \
             patch("handlers.auth.User", mock_user_cls), \
             patch("handlers.auth.UserAuthIdentity", mock_identity_cls):
            resp = await handle_signup(request, MockEnvLocalOtp(), {}, {}, "/api/auth/signup")

        assert resp.status == 400
        data = resp.data if hasattr(resp, "data") else json.loads(resp.body)
        assert data["message"] == "Local verification code is only available in local development"
        get_db_safe.assert_not_awaited()
        mock_user_cls.create.assert_not_called()
        mock_identity_cls.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_signup_is_rate_limited_after_burst(self, monkeypatch):
        monkeypatch.setattr("handlers.auth._SIGNUP_MAX_REQUESTS", 2)
        body = {"username": "user123", "password": "Testpass123456!", "email": "user@example.com"}
        request = MockRequest(method="POST", body=body)

        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())), \
             patch("handlers.auth.check_required_fields", AsyncMock(return_value=(True, None))), \
             patch("handlers.auth.blind_index", side_effect=lambda value, *_args, **_kwargs: f"{value}-hash"), \
             patch("handlers.auth.encrypt_sensitive", side_effect=lambda value, *_args, **_kwargs: value), \
             patch("handlers.auth.User") as mock_user_cls, \
             patch("handlers.auth.UserAuthIdentity") as mock_identity_cls, \
             patch("handlers.auth.EmailService") as mock_email_service, \
             patch("handlers.auth.generate_jwt_token", return_value="fake.token"):
            mock_qs = MagicMock()
            mock_qs.filter.return_value = mock_qs
            mock_qs.first = AsyncMock(return_value=None)
            mock_qs.delete = AsyncMock()
            mock_user_cls.objects.return_value = mock_qs
            mock_user_cls.create = AsyncMock(return_value={"id": 1})
            mock_identity_cls.create = AsyncMock(return_value={"id": 100})
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

    @pytest.mark.asyncio
    async def test_non_verification_token_returns_400(self):
        request = MockRequest(method="GET", body=None)
        mock_user_cls = MagicMock()
        mock_qs = MagicMock()
        mock_qs.filter.return_value = mock_qs
        mock_qs.update = AsyncMock()
        mock_user_cls.objects.return_value = mock_qs

        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())), \
             patch("handlers.auth.decode_jwt", return_value={"user_id": 1, "purpose": "access"}), \
             patch("handlers.auth.User", mock_user_cls):
            resp = await handle_verify_email(
                request, MockEnv(), {}, {"token": "access.token"}, "/auth/verify-email"
            )

        assert resp.status == 400
        mock_qs.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_verification_sets_active_and_email_verified_at(self):
        request = MockRequest(method="GET", body=None)
        mock_user_cls = MagicMock()
        mock_qs = MagicMock()
        mock_qs.filter.return_value = mock_qs
        mock_qs.update = AsyncMock()
        mock_user_cls.objects.return_value = mock_qs

        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())), \
             patch("handlers.auth.decode_jwt", return_value={"user_id": 1, "purpose": "email_verification"}), \
             patch("handlers.auth.User", mock_user_cls):
            resp = await handle_verify_email(
                request, MockEnv(), {}, {"token": "verify.token"}, "/auth/verify-email"
            )

        assert resp.status == 200
        mock_qs.update.assert_awaited_once()
        update_kwargs = mock_qs.update.await_args.kwargs
        assert update_kwargs["is_active"] is True
        assert isinstance(update_kwargs["email_verified_at"], str)


class TestApiKeyManagement:
    """Tests for JWT-protected user API key management."""

    @pytest.mark.asyncio
    async def test_api_keys_require_bearer_jwt(self):
        request = MockRequest(method="GET")

        resp = await auth_module.handle_api_keys(request, MockEnv(), {}, {}, "/auth/api-keys")

        assert resp.status == 401

    @pytest.mark.asyncio
    async def test_list_api_keys_returns_active_user_owned_keys_without_hashes(self):
        mock_key_cls = MagicMock()
        mock_qs = MagicMock()
        mock_qs.filter.return_value = mock_qs
        mock_qs.order_by.return_value = mock_qs
        mock_qs.values.return_value = mock_qs
        mock_qs.all = AsyncMock(return_value=[
            {
                "id": 10,
                "name": "ci",
                "key_prefix": "blt_live_abcd",
                "scopes": "[]",
                "is_active": 1,
                "created": "2026-05-30 00:00:00",
                "last_used": None,
                "revoked_at": None,
            }
        ])
        mock_key_cls.objects.return_value = mock_qs

        request = _make_auth_request(method="GET", user_id=42)
        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())), \
             patch("handlers.auth.UserApiKey", mock_key_cls, create=True):
            resp = await auth_module.handle_api_keys(request, MockEnv(), {}, {}, "/auth/api-keys")

        assert resp.status == 200
        assert resp.data["data"][0]["id"] == 10
        assert "key_hash" not in resp.data["data"][0]
        assert "api_key" not in resp.data["data"][0]
        mock_qs.filter.assert_called_once_with(user_id=42, is_active=True)

    @pytest.mark.asyncio
    async def test_create_api_key_returns_raw_key_once(self):
        mock_key_cls = MagicMock()
        mock_key_cls.create = AsyncMock(return_value={
            "id": 11,
            "name": "local dev",
            "key_prefix": "blt_live_new",
            "created": "2026-05-30 00:00:00",
        })
        request = _make_auth_request(
            method="POST",
            body={"name": "local dev"},
            user_id=42,
        )

        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())), \
             patch("handlers.auth.UserApiKey", mock_key_cls, create=True), \
             patch("handlers.auth.generate_user_api_key", return_value="blt_live_newsecret"), \
             patch("handlers.auth.hash_user_api_key", return_value="key-hash"):
            resp = await auth_module.handle_api_keys(request, MockEnv(), {}, {}, "/auth/api-keys")

        assert resp.status == 201
        assert resp.data["data"]["api_key"] == "blt_live_newsecret"
        create_kwargs = mock_key_cls.create.await_args.kwargs
        assert create_kwargs["user_id"] == 42
        assert create_kwargs["name"] == "local dev"
        assert create_kwargs["key_hash"] == "key-hash"

    @pytest.mark.asyncio
    async def test_revoke_api_key_only_revokes_user_owned_key(self):
        mock_key_cls = MagicMock()
        mock_qs = MagicMock()
        mock_qs.filter.return_value = mock_qs
        mock_qs.first = AsyncMock(return_value={"id": 11, "user_id": 42, "is_active": 1})
        mock_qs.update = AsyncMock()
        mock_key_cls.objects.return_value = mock_qs
        request = _make_auth_request(method="DELETE", user_id=42)

        with patch("handlers.auth.get_db_safe", AsyncMock(return_value=MagicMock())), \
             patch("handlers.auth.UserApiKey", mock_key_cls, create=True):
            resp = await auth_module.handle_api_keys(
                request,
                MockEnv(),
                {"id": "11"},
                {},
                "/auth/api-keys/11",
            )

        assert resp.status == 200
        mock_qs.filter.assert_called_once_with(id=11, user_id=42, is_active=True)
        update_kwargs = mock_qs.update.await_args.kwargs
        assert update_kwargs["is_active"] is False
        assert isinstance(update_kwargs["revoked_at"], str)
