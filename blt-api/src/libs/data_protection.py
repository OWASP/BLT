"""Utilities for encrypting and indexing sensitive user data."""

import base64
import hashlib
import hmac
import json
import secrets
from typing import Any, Optional


def _derive_key_material(seed: str) -> bytes:
    """Derive stable 32-byte key material from a secret seed."""
    return hashlib.sha256(seed.encode("utf-8")).digest()


def _get_secret_seed(env: Any) -> str:
    """Resolve the secret seed from environment bindings."""
    seed = str(
        getattr(env, "USER_DATA_ENCRYPTION_KEY", "")
        or getattr(env, "JWT_SECRET", "")
        or "owasp-blt-default-encryption-key"
    )
    return seed


def _get_enc_key(env: Any) -> bytes:
    return _derive_key_material("enc:" + _get_secret_seed(env))


def _get_mac_key(env: Any) -> bytes:
    return _derive_key_material("mac:" + _get_secret_seed(env))


def _xor_bytes(data: bytes, key_stream: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(data, key_stream))


def _keystream(enc_key: bytes, nonce: bytes, length: int) -> bytes:
    """Generate a deterministic keystream using HMAC-SHA256 blocks."""
    output = bytearray()
    counter = 0
    while len(output) < length:
        block = hmac.new(enc_key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        output.extend(block)
        counter += 1
    return bytes(output[:length])


def encrypt_sensitive(value: Optional[str], env: Any) -> Optional[str]:
    """Encrypt sensitive string values for at-rest storage.

    Uses a stdlib-only authenticated encryption scheme to avoid external
    runtime dependencies in Cloudflare Workers Python.
    """
    if value is None:
        return None
    plaintext = str(value)
    if plaintext == "":
        return ""

    plaintext_bytes = plaintext.encode("utf-8")
    nonce = secrets.token_bytes(16)
    enc_key = _get_enc_key(env)
    mac_key = _get_mac_key(env)

    stream = _keystream(enc_key, nonce, len(plaintext_bytes))
    ciphertext = _xor_bytes(plaintext_bytes, stream)
    tag = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()

    payload = {
        "v": 1,
        "n": base64.urlsafe_b64encode(nonce).decode("ascii"),
        "c": base64.urlsafe_b64encode(ciphertext).decode("ascii"),
        "t": base64.urlsafe_b64encode(tag).decode("ascii"),
    }
    return base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii")


def decrypt_sensitive(value: Optional[str], env: Any) -> Optional[str]:
    """Decrypt sensitive string values from storage."""
    if value is None:
        return None
    token = str(value)
    if token == "":
        return ""

    decoded = base64.urlsafe_b64decode(token.encode("ascii"))
    payload = json.loads(decoded.decode("utf-8"))
    if payload.get("v") != 1:
        raise ValueError("Unsupported encrypted payload version")

    nonce = base64.urlsafe_b64decode(payload["n"].encode("ascii"))
    ciphertext = base64.urlsafe_b64decode(payload["c"].encode("ascii"))
    tag = base64.urlsafe_b64decode(payload["t"].encode("ascii"))

    mac_key = _get_mac_key(env)
    expected_tag = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected_tag):
        raise ValueError("Invalid encrypted payload tag")

    enc_key = _get_enc_key(env)
    stream = _keystream(enc_key, nonce, len(ciphertext))
    plaintext = _xor_bytes(ciphertext, stream)
    return plaintext.decode("utf-8")


def blind_index(value: str, env: Any, scope: str) -> str:
    """Create a keyed blind index for secure equality checks."""
    normalized = value.strip().lower().encode("utf-8")
    seed = str(
        getattr(env, "USER_DATA_HASH_KEY", "")
        or getattr(env, "USER_DATA_ENCRYPTION_KEY", "")
        or getattr(env, "JWT_SECRET", "")
        or "owasp-blt-default-hash-key"
    )
    key = _derive_key_material(f"{scope}:{seed}")
    return hmac.new(key, normalized, hashlib.sha256).hexdigest()


def encrypted_email_placeholder(email_hash: str) -> str:
    """Generate a non-sensitive placeholder for legacy NOT NULL email column."""
    return f"enc+{email_hash[:24]}@owaspblt.local"
