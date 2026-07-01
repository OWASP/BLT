"""
Pytest test suite for src/redaction_engine.py.

This native engine relies entirely on regex patterns. No HTTP mocking or
Docker containers are required.
"""

import pytest

from src.redaction_engine import (
    analyze_text,
    anonymize_text,
    build_redaction_map,
    is_deny_listed,
)


# ─── analyze_text tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_text_detects_email():
    """Emails must be detected by the native regex."""
    text = "Contact me at test@example.com for info."
    results = await analyze_text(text)

    assert len(results) == 1
    assert results[0]["entity_type"] == "EMAIL_ADDRESS"
    assert results[0]["score"] == 1.0
    assert text[results[0]["start"] : results[0]["end"]] == "test@example.com"


@pytest.mark.asyncio
async def test_analyze_text_detects_phone():
    """Phone numbers must be detected by the native regex."""
    text = "Call me at +1-555-867-5309"
    results = await analyze_text(text)

    assert len(results) == 1
    assert results[0]["entity_type"] == "PHONE_NUMBER"
    assert results[0]["score"] == 0.85
    assert text[results[0]["start"] : results[0]["end"]] == "+1-555-867-5309"


@pytest.mark.asyncio
async def test_analyze_text_detects_multiple():
    """Multiple entity types in the same string must be detected and sorted by start index."""
    text = "IP 192.168.1.1 and email admin@owasp.org"
    results = await analyze_text(text)

    assert len(results) == 2
    assert results[0]["entity_type"] == "IP_ADDRESS"
    assert text[results[0]["start"] : results[0]["end"]] == "192.168.1.1"

    assert results[1]["entity_type"] == "EMAIL_ADDRESS"
    assert text[results[1]["start"] : results[1]["end"]] == "admin@owasp.org"


# ─── anonymize_text tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_anonymize_text_success():
    """Anonymize replaces detected entities with <REDACTED>."""
    text = "My email is test@example.com"
    analyzer_results = await analyze_text(text)

    result = await anonymize_text(text, analyzer_results)

    assert result["text"] == "My email is <REDACTED>"
    assert len(result["items"]) == 1
    assert result["items"][0]["entity_type"] == "EMAIL_ADDRESS"


@pytest.mark.asyncio
async def test_anonymize_text_multiple():
    """Anonymize multiple entities from back-to-front string replacement."""
    text = "IP 192.168.1.1 and email admin@owasp.org"
    analyzer_results = await analyze_text(text)

    result = await anonymize_text(text, analyzer_results)

    assert result["text"] == "IP <REDACTED> and email <REDACTED>"
    assert len(result["items"]) == 2


# ─── build_redaction_map tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_build_redaction_map_returns_sorted_records():
    """build_redaction_map must sort by byte_start ascending."""
    analyzer_results = [
        {"entity_type": "PERSON", "start": 50, "end": 60, "score": 0.9},
        {"entity_type": "EMAIL_ADDRESS", "start": 10, "end": 30, "score": 0.95},
    ]
    result = await build_redaction_map("dummy text", analyzer_results)

    assert result[0]["byte_start"] == 10
    assert result[1]["byte_start"] == 50
    assert result[0]["detector"] == "native_regex"


@pytest.mark.asyncio
async def test_build_redaction_map_empty_results():
    """build_redaction_map with no entities returns empty list."""
    result = await build_redaction_map("clean text with no PII", [])
    assert result == []


# ─── Custom recognizer pattern tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_jwt_token_detected():
    """JWT tokens must be detected."""
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.abc123XYZabc123XYZ"
    results = await analyze_text(jwt)
    assert len(results) == 1
    assert results[0]["entity_type"] == "JWT_TOKEN"


@pytest.mark.asyncio
async def test_aws_access_key_detected():
    """AWS Access Key IDs (AKIA...) must be detected."""
    results = await analyze_text("AKIAIOSFODNN7EXAMPLE")
    assert len(results) == 1
    assert results[0]["entity_type"] == "AWS_ACCESS_KEY"


@pytest.mark.asyncio
async def test_github_token_detected():
    """GitHub PATs must be detected."""
    results = await analyze_text("ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890abcd")
    assert len(results) == 1
    assert results[0]["entity_type"] == "GITHUB_TOKEN"


@pytest.mark.asyncio
async def test_private_key_detected():
    """PEM private key headers must be detected."""
    results = await analyze_text("-----BEGIN RSA PRIVATE KEY-----")
    assert len(results) == 1
    assert results[0]["entity_type"] == "PRIVATE_KEY"


@pytest.mark.asyncio
async def test_bearer_token_detected():
    """Bearer token strings must be detected."""
    results = await analyze_text("Authorization: Bearer eyJsometoken123456789012345")
    assert len(results) == 1
    assert results[0]["entity_type"] == "BEARER_TOKEN"


# ─── Deny-list false positive tests ──────────────────────────────────────────


def test_cve_string_is_deny_listed():
    """CVE identifiers must never be flagged as PII."""
    assert is_deny_listed("CVE-2024-1234")


def test_cwe_string_is_deny_listed():
    """CWE identifiers must never be flagged as PII."""
    assert is_deny_listed("CWE-79")


def test_owasp_string_is_deny_listed():
    """OWASP references must never be flagged as PII."""
    assert is_deny_listed("OWASP-A01")


def test_hex_literal_is_deny_listed():
    """Hex literals (memory addresses) must never be flagged as PII."""
    assert is_deny_listed("0xDEADBEEF")


@pytest.mark.asyncio
async def test_normal_email_is_not_deny_listed():
    """A real email address must NOT be caught by the deny-list."""
    assert not is_deny_listed("user@example.com")
    results = await analyze_text("user@example.com")
    assert len(results) == 1


@pytest.mark.asyncio
async def test_deny_list_prevents_detection():
    """Ensure analyze_text drops anything on the deny list."""
    # Assuming the 0xDEADBEEF might trigger some regex by accident,
    # it shouldn't because of the deny list.
    results = await analyze_text("CVE-2024-1234")
    assert len(results) == 0
