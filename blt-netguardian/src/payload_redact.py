"""Redact sensitive keys from finding payload snippets for API/UI."""

from __future__ import annotations

from typing import Any

REDACT_KEYS = frozenset({
    "password",
    "secret",
    "token",
    "api_key",
    "authorization",
    "private_key",
    "credential",
})


def redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return redact_payload(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    return value


def redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        if key.lower() in REDACT_KEYS:
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            redacted[key] = redact_payload(value)
        elif isinstance(value, list):
            redacted[key] = [redact_value(item) for item in value]
        else:
            redacted[key] = value
    return redacted
