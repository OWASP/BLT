"""Worker-level tests for /api/ingest."""

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from envelope import prepare_signed_envelope
from canonicalize import body_digest_hex
from test_ingest_api import IngestFakeDB
from test_worker_api import BLTWorker, FakeRequest, parse_json

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "canonical_vectors.json"


@pytest.fixture(scope="module")
def fixture_data():
    return json.loads(FIXTURES.read_text())


@pytest.fixture
def secret(fixture_data):
    return bytes.fromhex(fixture_data["secret_hex"])


@pytest.fixture
def signed_envelope(fixture_data, secret):
    env_body = dict(fixture_data["envelope_unsigned"])
    env_body.pop("payload_digest", None)
    env_body["issued_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return prepare_signed_envelope(env_body, secret)


@pytest.mark.asyncio
async def test_handle_ingest_created(signed_envelope, secret, fixture_data):
    body_bytes = json.dumps(signed_envelope, separators=(",", ":"), ensure_ascii=False).encode()
    db = IngestFakeDB()
    env = SimpleNamespace(
        DB=db,
        NG_SENDER_SECRETS=json.dumps({"org-demo:scanner-1:k1": fixture_data["secret_hex"]}),
        NG_INGEST_RPM="60",
    )
    worker = BLTWorker(env)
    request = FakeRequest(
        "https://api.example.com/api/ingest",
        method="POST",
        body_bytes=body_bytes,
        headers={"X-BLT-Body-Digest": f"sha256={body_digest_hex(body_bytes)}"},
    )

    response = await worker.handle_ingest(request)
    payload = parse_json(response)

    assert response.status == 201
    assert payload["status"] == "created"
    assert payload["replay"] is False


@pytest.mark.parametrize("header_name", [
    "X-BLT-Body-Digest",
    "x-blt-body-digest",
    "X-Blt-Body-Digest",   # http.client / urllib normalization
    "X-blt-body-digest",   # urllib.request.Request.add_header (str.capitalize)
])
@pytest.mark.asyncio
async def test_handle_ingest_accepts_any_digest_header_casing(
    header_name, signed_envelope, secret, fixture_data
):
    """HTTP field names are case-insensitive; clients disagree on casing.

    urllib capitalizes header names, so a case-sensitive lookup rejected valid
    senders with digest_mismatch for a header they had actually sent.
    """
    body_bytes = json.dumps(signed_envelope, separators=(",", ":"), ensure_ascii=False).encode()
    env = SimpleNamespace(
        DB=IngestFakeDB(),
        NG_SENDER_SECRETS=json.dumps({"org-demo:scanner-1:k1": fixture_data["secret_hex"]}),
        NG_INGEST_RPM="60",
    )
    request = FakeRequest(
        "https://api.example.com/api/ingest",
        method="POST",
        body_bytes=body_bytes,
        headers={header_name: f"sha256={body_digest_hex(body_bytes)}"},
    )

    response = await BLTWorker(env).handle_ingest(request)
    assert response.status == 201, parse_json(response)


@pytest.mark.asyncio
async def test_handle_ingest_missing_digest_header_is_rejected(
    signed_envelope, secret, fixture_data
):
    """Case-insensitivity must not degrade into accepting no digest at all."""
    body_bytes = json.dumps(signed_envelope, separators=(",", ":"), ensure_ascii=False).encode()
    env = SimpleNamespace(
        DB=IngestFakeDB(),
        NG_SENDER_SECRETS=json.dumps({"org-demo:scanner-1:k1": fixture_data["secret_hex"]}),
        NG_INGEST_RPM="60",
    )
    request = FakeRequest(
        "https://api.example.com/api/ingest",
        method="POST",
        body_bytes=body_bytes,
        headers={"Content-Type": "application/json"},
    )

    response = await BLTWorker(env).handle_ingest(request)
    assert response.status == 400
    assert parse_json(response)["error"] == "digest_mismatch"


@pytest.mark.asyncio
async def test_handle_ingest_no_db():
    worker = BLTWorker(SimpleNamespace(DB=None))
    request = FakeRequest(
        "https://api.example.com/api/ingest",
        method="POST",
        payload={"version": "ztr-finding-1"},
    )
    response = await worker.handle_ingest(request)
    assert response.status == 503
