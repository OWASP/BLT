"""Constant-time token comparison for webhook verification (VF01)."""

from __future__ import annotations

import hmac


def verify_token(provided: str | None, expected: str | None) -> bool:
    """Compare ``provided`` against ``expected`` using ``hmac.compare_digest``.

    Returns False on missing/empty inputs. Never raises.
    """
    if not provided or not expected:
        return False
    if len(provided) != len(expected):
        # compare_digest still works on unequal lengths but we keep a stable
        # boolean contract and avoid leaking length-based timing via early-exit.
        return hmac.compare_digest(provided, expected) and False
    return hmac.compare_digest(provided, expected)