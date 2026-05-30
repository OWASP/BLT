from datetime import datetime

import pytest

from src.services.security import (
    get_client_ip,
    minute_bucket_iso,
    normalize_domain,
    sha256_hex,
)


def test_normalize_domain_strips_and_lowercases():
    assert normalize_domain("  Example.COM  ") == "example.com"


def test_normalize_domain_empty_string():
    assert normalize_domain("") == ""
    assert normalize_domain("   ") == ""


def test_get_client_ip_from_header():
    class Req:
        def __init__(self, headers):
            self.headers = headers

    req = Req(headers={"CF-Connecting-IP": "203.0.113.10"})
    assert get_client_ip(req) == "203.0.113.10"


def test_get_client_ip_default_when_missing():
    class Req:
        def __init__(self, headers):
            self.headers = headers

    req = Req(headers={})
    assert get_client_ip(req) == "0.0.0.0"


def test_minute_bucket_iso_with_fixed_datetime():
    dt = datetime(2026, 3, 1, 12, 34, 56)
    assert minute_bucket_iso(dt) == "2026-03-01T12:34"


def test_minute_bucket_iso_default_uses_current_time():
    """Call with no args; assert returned string has YYYY-MM-DDTHH:MM shape."""
    result = minute_bucket_iso()
    assert len(result) == 16
    assert result[4] == "-" and result[7] == "-" and result[10] == "T" and result[13] == ":"


@pytest.mark.asyncio
async def test_sha256_hex_matches_known_value():
    data = b"blt-zero-test"
    digest = await sha256_hex(data)
    # Precomputed with Python's hashlib.sha256(b"blt-zero-test").hexdigest()
    assert digest == "8a4861757f42a36e5b7b872d1b4a21a27d3a4b9bfa72eb99fc1bcf253170bdfa"
