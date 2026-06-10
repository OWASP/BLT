import base64
import json
from pathlib import Path

import pytest

from ingest.canonicalize import (
    body_digest_hex,
    canonicalize_envelope_for_signing,
    canonicalize_json,
    hmac_sha256_hex,
    payload_digest_hex,
    verify_hmac_sha256_hex,
)

FIXTURES = Path(__file__).parent / "fixtures" / "canonical_vectors.json"


@pytest.fixture
def vectors():
    return json.loads(FIXTURES.read_text())


def test_canonicalize_json_sorts_keys():
    raw = canonicalize_json({"b": 1, "a": 2})
    assert raw == b'{"a":2,"b":1}'


def test_canonicalize_json_unicode():
    raw = canonicalize_json({"title": "café"})
    decoded = raw.decode("utf-8")
    assert "café" in decoded
    assert json.loads(decoded)["title"] == "café"


def test_signature_field_excluded_from_signing_input():
    envelope = {
        "version": "ztr-finding-1",
        "nonce": "n1",
        "signature": "deadbeef",
    }
    unsigned = canonicalize_envelope_for_signing(envelope)
    assert b"signature" not in unsigned
    assert b'"nonce":"n1"' in unsigned


def test_payload_digest_plaintext_stable(vectors):
    payload = vectors["envelope_unsigned"]["payload_plaintext"]
    d1 = payload_digest_hex(plaintext=payload, ciphertext_b64=None)
    d2 = payload_digest_hex(plaintext=payload, ciphertext_b64=None)
    assert d1 == d2
    assert len(d1) == 64


def test_payload_digest_ciphertext():
    raw = b"secret-bytes"
    b64 = base64.b64encode(raw).decode("ascii")
    assert payload_digest_hex(plaintext=None, ciphertext_b64=b64) == body_digest_hex(raw)


def test_hmac_roundtrip(vectors):
    secret = bytes.fromhex(vectors["secret_hex"])
    env = dict(vectors["envelope_unsigned"])
    env.pop("payload_digest", None)
    message = canonicalize_envelope_for_signing(env)
    sig = hmac_sha256_hex(secret, message)
    assert verify_hmac_sha256_hex(secret, message, sig)
    assert not verify_hmac_sha256_hex(secret, message, "00" * 64)


def test_tampered_kid_changes_signature(vectors):
    secret = bytes.fromhex(vectors["secret_hex"])
    env = dict(vectors["envelope_unsigned"])
    message = canonicalize_envelope_for_signing(env)
    sig = hmac_sha256_hex(secret, message)
    env["kid"] = "k-tampered"
    tampered = canonicalize_envelope_for_signing(env)
    assert not verify_hmac_sha256_hex(secret, tampered, sig)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"plaintext": {"a": 1}, "ciphertext_b64": "YQ=="},
        {"plaintext": None, "ciphertext_b64": None},
    ],
)
def test_payload_digest_rejects_invalid_modes(kwargs):
    with pytest.raises(ValueError):
        payload_digest_hex(**kwargs)


@pytest.mark.parametrize("bad_float", [float("nan"), float("inf"), float("-inf")])
def test_canonicalize_json_rejects_non_finite(bad_float):
    with pytest.raises(ValueError):
        canonicalize_json({"score": bad_float})
