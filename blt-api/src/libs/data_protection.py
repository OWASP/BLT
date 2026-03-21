"""Utilities for encrypting and indexing sensitive user data."""

import base64
import hashlib
import hmac
from typing import Any, Optional

from cryptography.fernet import Fernet


def _derive_key_material(seed: str) -> bytes:
    """Derive stable 32-byte key material from a secret seed."""
    return hashlib.sha256(seed.encode("utf-8")).digest()


def _get_fernet(env: Any) -> Fernet:
    """Build a Fernet instance from env-provided secrets."""
    seed = str(
        getattr(env, "USER_DATA_ENCRYPTION_KEY", "")
        or getattr(env, "JWT_SECRET", "")
        or "owasp-blt-default-encryption-key"
    )
    key = base64.urlsafe_b64encode(_derive_key_material(seed))
    return Fernet(key)


def encrypt_sensitive(value: Optional[str], env: Any) -> Optional[str]:
    """Encrypt sensitive string values for at-rest storage."""
    if value is None:
        return None
    plaintext = str(value)
    if plaintext == "":
        return ""
    return _get_fernet(env).encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_sensitive(value: Optional[str], env: Any) -> Optional[str]:
    """Decrypt sensitive string values from storage."""
    if value is None:
        return None
    token = str(value)
    if token == "":
        return ""
    return _get_fernet(env).decrypt(token.encode("utf-8")).decode("utf-8")


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
