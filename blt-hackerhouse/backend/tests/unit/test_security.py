"""Webhook security / token verification tests."""

from __future__ import annotations

from src.core.security import verify_token


def test_matches():
    assert verify_token("s3cr3t", "s3cr3t") is True


def test_mismatches():
    assert verify_token("nope", "s3cr3t") is False


def test_empty_inputs():
    assert verify_token("", "s3cr3t") is False
    assert verify_token("s3cr3t", "") is False
    assert verify_token(None, "s3cr3t") is False


def test_length_difference_does_not_match():
    assert verify_token("short", "much-longer-secret") is False