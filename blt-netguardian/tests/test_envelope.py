import base64
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from canonicalize import payload_digest_hex
from envelope import (
    check_clock_skew,
    parse_issued_at_utc,
    prepare_signed_envelope,
    sign_envelope,
    validate_envelope_shape,
    verify_body_digest,
    verify_envelope_signature,
    verify_payload_digest_field,
)
from errors import IngestError, IngestErrorCode

FIXTURES = Path(__file__).parent / "fixtures" / "canonical_vectors.json"


@pytest.fixture
def secret():
    return bytes.fromhex(json.loads(FIXTURES.read_text())["secret_hex"])


@pytest.fixture
def base_envelope():
    data = json.loads(FIXTURES.read_text())
    env = dict(data["envelope_unsigned"])
    env.pop("payload_digest", None)
    return env


def test_validate_rejects_dual_payload(base_envelope):
    env = {**base_envelope, "payload_ciphertext": base64.b64encode(b"x").decode()}
    with pytest.raises(IngestError) as exc:
        validate_envelope_shape(env)
    assert exc.value.code == IngestErrorCode.INVALID_PAYLOAD_MODE


def test_validate_rejects_bad_issued_at(base_envelope):
    base_envelope["issued_at"] = "2026-05-28T12:00:00+05:00"
    with pytest.raises(IngestError) as exc:
        validate_envelope_shape(base_envelope)
    assert exc.value.code == IngestErrorCode.INVALID_ENVELOPE


def test_clock_skew_rejects_stale():
    old = datetime.now(timezone.utc) - timedelta(minutes=10)
    with pytest.raises(IngestError) as exc:
        check_clock_skew(old)
    assert exc.value.code == IngestErrorCode.CLOCK_SKEW


def test_payload_digest_mismatch(base_envelope):
    base_envelope["payload_digest"] = "0" * 64
    with pytest.raises(IngestError) as exc:
        verify_payload_digest_field(base_envelope)
    assert exc.value.code == IngestErrorCode.DIGEST_MISMATCH


def test_body_digest_header(base_envelope):
    body = json.dumps(base_envelope, separators=(",", ":")).encode()
    from canonicalize import body_digest_hex

    verify_body_digest(body, f"sha256={body_digest_hex(body)}")
    with pytest.raises(IngestError):
        verify_body_digest(body, "sha256=" + "f" * 64)


def test_sign_and_verify_roundtrip(base_envelope, secret):
    base_envelope["issued_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    signed = prepare_signed_envelope({**base_envelope}, secret)
    verify_envelope_signature(signed, secret)
    assert len(signed["signature"]) == 64


def test_tamper_breaks_signature(base_envelope, secret):
    base_envelope["issued_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    signed = prepare_signed_envelope({**base_envelope}, secret)
    signed["nonce"] = "tampered"
    with pytest.raises(IngestError) as exc:
        verify_envelope_signature(signed, secret)
    assert exc.value.code == IngestErrorCode.BAD_SIGNATURE


def test_parse_issued_at_utc():
    dt = parse_issued_at_utc("2026-05-28T12:00:00.123Z")
    assert dt.tzinfo == timezone.utc


def test_sign_envelope_matches_prepare(base_envelope, secret):
    base_envelope["issued_at"] = "2026-05-28T12:00:00Z"
    digest = payload_digest_hex(
        plaintext=base_envelope["payload_plaintext"],
        ciphertext_b64=None,
    )
    base_envelope["payload_digest"] = digest
    verify_payload_digest_field(base_envelope)
    sig = sign_envelope(base_envelope, secret)
    env = {**base_envelope, "signature": sig}
    verify_envelope_signature(env, secret)
