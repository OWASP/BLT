"""Worker-level tests for /api/ng/ingest."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingest.envelope import prepare_signed_envelope
from ingest.canonicalize import body_digest_hex
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
async def test_handle_ng_ingest_created(signed_envelope, secret, fixture_data):
    body_bytes = json.dumps(signed_envelope, separators=(",", ":"), ensure_ascii=False).encode()
    db = IngestFakeDB()
    env = SimpleNamespace(
        DB=db,
        NG_SENDER_SECRETS=json.dumps({"org-demo:scanner-1:k1": fixture_data["secret_hex"]}),
        NG_INGEST_RPM="60",
    )
    worker = BLTWorker(env)
    request = FakeRequest(
        "https://api.example.com/api/ng/ingest",
        method="POST",
        body_bytes=body_bytes,
        headers={"X-BLT-Body-Digest": f"sha256={body_digest_hex(body_bytes)}"},
    )

    response = await worker.handle_ng_ingest(request)
    payload = parse_json(response)

    assert response.status == 201
    assert payload["status"] == "created"
    assert payload["replay"] is False


@pytest.mark.asyncio
async def test_handle_ng_ingest_no_db():
    worker = BLTWorker(SimpleNamespace(DB=None))
    request = FakeRequest(
        "https://api.example.com/api/ng/ingest",
        method="POST",
        payload={"version": "ztr-finding-1"},
    )
    response = await worker.handle_ng_ingest(request)
    assert response.status == 503
