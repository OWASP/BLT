"""Midterm E2E: ingest → list → detail → audit → convert → CSV."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from canonicalize import body_digest_hex
from envelope import prepare_signed_envelope
from findings_service import (
    convert_to_issue_for_request,
    export_csv_for_request,
    get_finding_for_request,
    list_findings_for_request,
)
from findings_store import FindingsStore
from ingest_service import process_ingest
from ingest_store import IngestStore
from netguardian_db import open_netguardian_db
from test_worker_api import BLTWorker, FakeRequest, parse_json

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "canonical_vectors.json"


def _sequential_ids():
    counter = {"n": 0}

    def new_id(label: str) -> str:
        counter["n"] += 1
        return f"{label}-{counter['n']}"

    return new_id


@pytest.fixture(scope="module")
def fixture_data():
    return json.loads(FIXTURES.read_text())


@pytest.fixture
def secret(fixture_data):
    return bytes.fromhex(fixture_data["secret_hex"])


@pytest.fixture
def env(fixture_data):
    return SimpleNamespace(
        NG_SENDER_SECRETS=json.dumps({"org-demo:scanner-1:k1": fixture_data["secret_hex"]}),
        NG_ORG_API_TOKENS=json.dumps({"triage-token": "org-demo", "other-token": "org-other"}),
        NG_INGEST_RPM="60",
    )


@pytest.fixture
def signed_envelope(fixture_data, secret):
    body = dict(fixture_data["envelope_unsigned"])
    body.pop("payload_digest", None)
    body["issued_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body["payload_plaintext"]["fingerprint"] = "fp-midterm-e2e"
    return prepare_signed_envelope(body, secret)


@pytest.fixture
def db():
    db = open_netguardian_db(REPO_ROOT)
    yield db
    db.conn.close()


@pytest.mark.asyncio
async def test_midterm_flow_service_layer(env, signed_envelope, db):
    raw = json.dumps(signed_envelope, separators=(",", ":"), ensure_ascii=False).encode()
    headers = {"Authorization": "Bearer triage-token"}

    ingest = await process_ingest(
        raw_body=raw,
        body_digest_header=f"sha256={body_digest_hex(raw)}",
        envelope=signed_envelope,
        env=env,
        db=db,
        store=IngestStore(db),
        new_id=_sequential_ids(),
    )
    assert ingest.status == 201
    finding_id = ingest.body["finding_id"]
    new_id = _sequential_ids()

    listed = await list_findings_for_request(
        env=env, db=db, headers=headers, query_params={}, store=FindingsStore(db),
    )
    assert listed.status == 200
    assert listed.body["total"] == 1

    detail = await get_finding_for_request(
        env=env, db=db, headers=headers, finding_id=finding_id,
        store=FindingsStore(db), new_id=new_id,
    )
    assert detail.status == 200
    assert detail.body["access"]["view_logged"] is True
    assert detail.body["payload_snippet"]["title"] == "Test finding"

    logs = await FindingsStore(db).list_access_logs("org-demo", finding_id)
    assert len(logs) >= 1
    assert logs[0]["action"] == "view_detail"

    convert = await convert_to_issue_for_request(
        env=env, db=db, headers=headers, finding_id=finding_id,
        store=FindingsStore(db), new_id=new_id,
    )
    assert convert.status == 201
    assert convert.body["blt_issue_id"]

    convert_again = await convert_to_issue_for_request(
        env=env, db=db, headers=headers, finding_id=finding_id,
        store=FindingsStore(db), new_id=_sequential_ids(),
    )
    assert convert_again.status == 200
    assert convert_again.body["status"] == "existing"

    csv_result = await export_csv_for_request(
        env=env, db=db, headers=headers, query_params={}, store=FindingsStore(db),
    )
    assert csv_result.status == 200
    rows = list(csv.DictReader(io.StringIO(csv_result.body["csv"])))
    assert len(rows) == 1
    assert rows[0]["id"] == finding_id
    assert "payload" not in csv_result.body["csv"].lower() or "password" not in csv_result.body["csv"].lower()


@pytest.mark.asyncio
async def test_midterm_flow_worker(env, signed_envelope, db):
    env.DB = db
    worker = BLTWorker(env)
    body_bytes = json.dumps(signed_envelope, separators=(",", ":"), ensure_ascii=False).encode()
    auth = {"Authorization": "Bearer triage-token"}

    ingest_resp = await worker.handle_ingest(
        FakeRequest(
            "https://local/api/ingest",
            method="POST",
            body_bytes=body_bytes,
            headers={"X-BLT-Body-Digest": f"sha256={body_digest_hex(body_bytes)}"},
        )
    )
    assert ingest_resp.status == 201
    finding_id = parse_json(ingest_resp)["finding_id"]

    detail_resp = await worker.handle_findings(
        FakeRequest(f"https://local/api/findings/{finding_id}", method="GET", headers=auth),
        f"api/findings/{finding_id}",
    )
    detail = parse_json(detail_resp)
    assert detail_resp.status == 200
    assert detail["finding"]["id"] == finding_id

    convert_resp = await worker.handle_findings(
        FakeRequest(
            f"https://local/api/findings/{finding_id}/convert-to-issue",
            method="POST",
            headers=auth,
        ),
        f"api/findings/{finding_id}/convert-to-issue",
    )
    assert convert_resp.status == 201

    csv_resp = await worker.handle_findings(
        FakeRequest("https://local/api/findings/export.csv", method="GET", headers=auth),
        "api/findings/export.csv",
    )
    assert csv_resp.status == 200
    assert "id,rule_id" in csv_resp.body


@pytest.mark.asyncio
async def test_fingerprint_dedupe_on_reingest(env, signed_envelope, secret, db):
    raw = json.dumps(signed_envelope, separators=(",", ":"), ensure_ascii=False).encode()
    digest = f"sha256={body_digest_hex(raw)}"

    first = await process_ingest(
        raw_body=raw, body_digest_header=digest, envelope=signed_envelope,
        env=env, db=db, store=IngestStore(db), new_id=lambda label: f"{label}-a",
    )
    assert first.status == 201

    envelope2 = dict(signed_envelope)
    envelope2["nonce"] = "different-nonce-xyz"
    envelope2 = prepare_signed_envelope(envelope2, secret)
    raw2 = json.dumps(envelope2, separators=(",", ":"), ensure_ascii=False).encode()
    second = await process_ingest(
        raw_body=raw2,
        body_digest_header=f"sha256={body_digest_hex(raw2)}",
        envelope=envelope2,
        env=env,
        db=db,
        store=IngestStore(db),
        new_id=lambda label: f"{label}-b",
    )
    assert second.status == 200
    assert second.body.get("dedupe") is True
    assert second.body["finding_id"] == first.body["finding_id"]
