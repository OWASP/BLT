"""Unit tests for AES-256-GCM evidence payload encryption."""

from __future__ import annotations

import base64
import json
from types import SimpleNamespace

import pytest

pytest.importorskip("cryptography")

from payload_crypto import (  # noqa: E402
    PayloadCryptoError,
    decrypt_payload,
    encrypt_payload,
    generate_key_b64,
    get_org_key,
    is_wrapped_ciphertext,
    load_org_keys,
    wrap_ciphertext,
)

KEY = b"netguardian-demo-aesgcm-key-0032"


def test_roundtrip_returns_original_payload():
    payload = {"rule_id": "sqli", "password": "hunter2", "n": 3}
    token = encrypt_payload(KEY, payload, aad=b"org-a")
    assert decrypt_payload(KEY, token, aad=b"org-a") == payload


def test_wrong_key_fails():
    token = encrypt_payload(KEY, {"a": 1}, aad=b"org-a")
    other = b"0000000000000000000000000000demo"
    with pytest.raises(PayloadCryptoError):
        decrypt_payload(other, token, aad=b"org-a")


def test_wrong_aad_fails():
    token = encrypt_payload(KEY, {"a": 1}, aad=b"org-a")
    with pytest.raises(PayloadCryptoError):
        decrypt_payload(KEY, token, aad=b"org-b")


def test_tampered_ciphertext_fails():
    token = encrypt_payload(KEY, {"a": 1}, aad=b"org-a")
    raw = bytearray(base64.b64decode(token))
    raw[-1] ^= 0x01
    tampered = base64.b64encode(bytes(raw)).decode()
    with pytest.raises(PayloadCryptoError):
        decrypt_payload(KEY, tampered, aad=b"org-a")


def test_bad_key_length_rejected():
    with pytest.raises(PayloadCryptoError):
        encrypt_payload(b"short", {"a": 1})


def test_generate_key_b64_is_32_bytes():
    assert len(base64.b64decode(generate_key_b64())) == 32


def test_wrapper_detection():
    wrapped = json.loads(wrap_ciphertext("abc"))
    assert is_wrapped_ciphertext(wrapped)
    assert not is_wrapped_ciphertext({"rule_id": "x"})
    assert not is_wrapped_ciphertext("abc")


def test_load_org_keys_filters_bad_entries():
    env = SimpleNamespace(NG_PAYLOAD_KEYS=json.dumps({
        "org-a": base64.b64encode(KEY).decode(),
        "org-bad": "not-base64!!",
        "org-short": base64.b64encode(b"short").decode(),
    }))
    keys = load_org_keys(env)
    assert set(keys) == {"org-a"}
    assert get_org_key(env, "org-a") == KEY
    assert get_org_key(env, "org-missing") is None
