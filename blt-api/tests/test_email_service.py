"""Tests for outbound email link construction."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from services.email_service import EmailService  # noqa: E402


@pytest.mark.asyncio
async def test_verification_email_links_to_browser_auth_page():
    service = EmailService(
        smtp_username="apikey",
        smtp_password="test-key",
        from_email="noreply@example.com",
    )
    service.send_email = AsyncMock(return_value=(202, ""))

    await service.send_verification_email(
        to_email="user@example.com",
        username="user",
        verification_token="verify.jwt.token",
        base_url="https://api.example.com",
    )

    html_content = service.send_email.await_args.args[2]
    assert "https://api.example.com/auth?verify_token=verify.jwt.token" in html_content
    assert "/auth/verify-email?token=" not in html_content
