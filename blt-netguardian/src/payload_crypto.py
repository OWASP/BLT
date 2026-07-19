"""AES-256-GCM authenticated encryption for finding evidence payloads.

Evidence payloads travel and rest as ciphertext; the server decrypts on an
authorized detail view and records the access in the audit log. This module is
the single crypto boundary:

- Local dev + tests use pyca/cryptography (AES-256-GCM AEAD).
- The Cloudflare Workers deployment maps the *same* AES-256-GCM parameters onto
  WebCrypto (``crypto.subtle``); a runtime adapter can back ``_aesgcm`` there.

The import of the backend is lazy so plaintext-mode ingest keeps working (and
the existing test suite stays green) in environments without ``cryptography``.
Ciphertext at rest is stored as a small JSON wrapper in ``envelopes.payload_json``
so detail queries can tell encrypted rows from legacy plaintext rows.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any, Mapping, Optional

ENC_ALG = "aes-256-gcm"
_NONCE_BYTES = 12
_KEY_BYTES = 32


class PayloadCryptoError(Exception):
    """Encryption/decryption failed, or the AEAD backend/key is unavailable."""


def _aesgcm(key: bytes):
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        return AESGCM(key)
    except ImportError:
        # Cloudflare Workers ships no 'cryptography'; use the pure-Python backend
        # (identical AES-256-GCM wire format) so encrypted evidence still works.
        from aesgcm_pure import AESGCMPure

        return AESGCMPure(key)


def generate_key_b64() -> str:
    """Return a fresh base64 AES-256 key (ops/provisioning helper)."""
    return base64.b64encode(os.urandom(_KEY_BYTES)).decode("ascii")


def load_org_keys(env: Any) -> dict[str, bytes]:
    """Parse ``NG_PAYLOAD_KEYS`` (JSON: org_id -> base64 32-byte key)."""
    raw = getattr(env, "NG_PAYLOAD_KEYS", None)
    if not raw:
        return {}
    try:
        mapping = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    keys: dict[str, bytes] = {}
    if isinstance(mapping, Mapping):
        for org_id, b64 in mapping.items():
            try:
                key = base64.b64decode(b64, validate=True)
            except (ValueError, TypeError):
                continue
            if len(key) == _KEY_BYTES:
                keys[str(org_id)] = key
    return keys


def get_org_key(env: Any, org_id: str) -> Optional[bytes]:
    return load_org_keys(env).get(org_id)


def encrypt_payload(key: bytes, payload: Mapping[str, Any], *, aad: bytes = b"") -> str:
    """Encrypt a payload dict; return base64(nonce || ciphertext || tag)."""
    if len(key) != _KEY_BYTES:
        raise PayloadCryptoError("key must be 32 bytes for AES-256-GCM")
    nonce = os.urandom(_NONCE_BYTES)
    plaintext = json.dumps(
        payload, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    ciphertext = _aesgcm(key).encrypt(nonce, plaintext, aad or None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt_payload(key: bytes, token_b64: str, *, aad: bytes = b"") -> dict:
    """Reverse :func:`encrypt_payload`; raise ``PayloadCryptoError`` on tamper."""
    if len(key) != _KEY_BYTES:
        raise PayloadCryptoError("key must be 32 bytes for AES-256-GCM")
    try:
        blob = base64.b64decode(token_b64, validate=True)
    except (ValueError, TypeError) as exc:
        raise PayloadCryptoError("ciphertext is not valid base64") from exc
    if len(blob) <= _NONCE_BYTES:
        raise PayloadCryptoError("ciphertext too short")
    nonce, ciphertext = blob[:_NONCE_BYTES], blob[_NONCE_BYTES:]
    try:
        plaintext = _aesgcm(key).decrypt(nonce, ciphertext, aad or None)
    except PayloadCryptoError:
        raise
    except Exception as exc:  # InvalidTag and backend-specific errors
        raise PayloadCryptoError(
            "decryption failed (wrong key or tampered ciphertext)"
        ) from exc
    try:
        obj = json.loads(plaintext)
    except ValueError as exc:
        raise PayloadCryptoError("decrypted payload is not valid JSON") from exc
    if not isinstance(obj, dict):
        raise PayloadCryptoError("decrypted payload must be a JSON object")
    return obj


def wrap_ciphertext(token_b64: str) -> str:
    """Serialize the at-rest wrapper stored in ``envelopes.payload_json``."""
    return json.dumps({"enc": ENC_ALG, "ciphertext": token_b64}, separators=(",", ":"))


def is_wrapped_ciphertext(obj: Any) -> bool:
    return (
        isinstance(obj, Mapping)
        and obj.get("enc") == ENC_ALG
        and isinstance(obj.get("ciphertext"), str)
    )
