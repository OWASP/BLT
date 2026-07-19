"""Resolve sender HMAC secrets from Worker env (secrets not stored in D1)."""

from __future__ import annotations

import json
from typing import Any


def lookup_sender_secret(env: Any, org_id: str, sender_id: str, kid: str) -> bytes | None:
    """Map org_id:sender_id:kid → secret bytes via NG_SENDER_SECRETS JSON."""
    raw = getattr(env, "NG_SENDER_SECRETS", None)
    if not raw:
        return None
    try:
        mapping = json.loads(str(raw))
    except json.JSONDecodeError:
        return None
    if not isinstance(mapping, dict):
        return None
    key = f"{org_id}:{sender_id}:{kid}"
    value = mapping.get(key)
    if value is None:
        return None
    text = str(value)
    if len(text) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in text):
        try:
            return bytes.fromhex(text)
        except ValueError:
            pass
    return text.encode("utf-8")
