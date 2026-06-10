"""JCS-profile canonicalization and digests for ztr-finding-1."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any, Mapping


def canonicalize_json(value: Any) -> bytes:
    """RFC 8785-compatible profile: sorted keys, compact separators, UTF-8."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonicalize_envelope_for_signing(envelope: Mapping[str, Any]) -> bytes:
    """Envelope document used as HMAC message (signature field omitted)."""
    unsigned = {k: v for k, v in envelope.items() if k != "signature"}
    return canonicalize_json(unsigned)


def body_digest_hex(raw_body: bytes) -> str:
    return hashlib.sha256(raw_body).hexdigest()


def payload_digest_hex(*, plaintext: Mapping[str, Any] | None, ciphertext_b64: str | None) -> str:
    if plaintext is not None and ciphertext_b64 is not None:
        raise ValueError("exactly one payload mode")
    if plaintext is not None:
        payload_bytes = canonicalize_json(plaintext)
    elif ciphertext_b64 is not None:
        payload_bytes = base64.b64decode(ciphertext_b64, validate=True)
    else:
        raise ValueError("missing payload")
    return hashlib.sha256(payload_bytes).hexdigest()


def hmac_sha256_hex(secret: bytes, message: bytes) -> str:
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def verify_hmac_sha256_hex(secret: bytes, message: bytes, signature_hex: str) -> bool:
    expected = hmac_sha256_hex(secret, message)
    return hmac.compare_digest(expected, signature_hex.lower())
