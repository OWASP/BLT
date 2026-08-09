"""Verified events outbox, webhook HMAC, and GET /api/events."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from canonicalize import body_digest_hex, hmac_sha256_hex
from envelope import prepare_signed_envelope
from events_service import (
    EVENT_ID_HEADER,
    SIGNATURE_HEADER,
    deliver_event_webhook,
    emit_converted_event,
    get_event_for_request,
    list_events_for_request,
    sign_webhook_body,
)
from events_store import EVENT_CONVERTED, EVENT_RESOLVED, EventsStore
from findings_service import convert_to_issue_for_request, update_finding_for_request
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
        AUTHENTICATE_READ_ENDPOINTS="false",
        NG_DEFAULT_ORG="org-demo",
    )


@pytest.fixture
def db():
    db = open_netguardian_db(REPO_ROOT)
    yield db
    db.conn.close()


async def _ingest_one(env, db, fixture_data, secret, *, fingerprint: str, nonce: str):
    body = dict(fixture_data["envelope_unsigned"])
    body.pop("payload_digest", None)
    body["nonce"] = nonce
    body["issued_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body["payload_plaintext"]["fingerprint"] = fingerprint
    signed = prepare_signed_envelope(body, secret)
    raw = json.dumps(signed, separators=(",", ":"), ensure_ascii=False).encode()
    result = await process_ingest(
        raw_body=raw,
        body_digest_header=f"sha256={body_digest_hex(raw)}",
        envelope=signed,
        env=env,
        db=db,
        store=IngestStore(db),
        new_id=_sequential_ids(),
    )
    assert result.status == 201
    return result.body["finding_id"]


@pytest.mark.asyncio
async def test_convert_emits_idempotent_converted_event(env, db, fixture_data, secret):
    finding_id = await _ingest_one(
        env, db, fixture_data, secret, fingerprint="fp-events-convert", nonce="nonce-events-1",
    )
    headers = {"Authorization": "Bearer triage-token"}
    ids = _sequential_ids()

    first = await convert_to_issue_for_request(
        env=env, db=db, headers=headers, finding_id=finding_id, new_id=ids,
    )
    assert first.status == 201
    assert first.body["event_created"] is True
    event_id = first.body["event_id"]

    second = await convert_to_issue_for_request(
        env=env, db=db, headers=headers, finding_id=finding_id, new_id=_sequential_ids(),
    )
    assert second.status == 200
    assert second.body["status"] == "existing"
    assert second.body["event_id"] == event_id
    assert second.body["event_created"] is False

    listed = await list_events_for_request(
        env=env,
        db=db,
        headers=headers,
        query_params={"finding_id": finding_id},
    )
    assert listed.status == 200
    assert listed.body["total"] == 1
    event = listed.body["events"][0]
    assert event["event_type"] == EVENT_CONVERTED
    assert event["status"] == "skipped"  # no webhook configured
    assert event["payload"]["version"] == "ng-event-1"
    assert event["payload"]["finding_id"] == finding_id
    assert event["payload"]["issue_id"] == first.body["blt_issue_id"]


@pytest.mark.asyncio
async def test_resolve_emits_resolved_event(env, db, fixture_data, secret):
    finding_id = await _ingest_one(
        env, db, fixture_data, secret, fingerprint="fp-events-resolve", nonce="nonce-events-2",
    )
    headers = {"Authorization": "Bearer triage-token"}
    ids = _sequential_ids()

    updated = await update_finding_for_request(
        env=env,
        db=db,
        headers=headers,
        finding_id=finding_id,
        body={"status": "wontfix"},
        new_id=ids,
    )
    assert updated.status == 200
    assert updated.body["event_created"] is True

    again = await update_finding_for_request(
        env=env,
        db=db,
        headers=headers,
        finding_id=finding_id,
        body={"status": "wontfix"},
        new_id=ids,
    )
    assert again.status == 200
    # Already resolved — no second emission.
    assert "event_id" not in again.body

    listed = await list_events_for_request(
        env=env,
        db=db,
        headers=headers,
        query_params={"event_type": EVENT_RESOLVED},
    )
    assert listed.status == 200
    assert listed.body["total"] == 1
    assert listed.body["events"][0]["payload"]["finding_id"] == finding_id


@pytest.mark.asyncio
async def test_webhook_hmac_delivery_and_signature(env, db, fixture_data, secret):
    finding_id = await _ingest_one(
        env, db, fixture_data, secret, fingerprint="fp-events-hook", nonce="nonce-events-3",
    )
    webhook_secret = b"webhook-test-secret"
    env.NG_EVENTS_WEBHOOK_URL = "https://hooks.example/netguardian"
    env.NG_EVENTS_WEBHOOK_SECRET = webhook_secret.decode("utf-8")

    seen = {}

    async def fake_fetch(url, method, headers, body):
        seen["url"] = url
        seen["method"] = method
        seen["headers"] = dict(headers)
        seen["body"] = body
        return 200, "ok"

    convert = await convert_to_issue_for_request(
        env=env,
        db=db,
        headers={"Authorization": "Bearer triage-token"},
        finding_id=finding_id,
        new_id=_sequential_ids(),
        events_fetch_impl=fake_fetch,
    )
    assert convert.status == 201
    assert seen["url"] == "https://hooks.example/netguardian"
    assert seen["method"] == "POST"
    assert seen["headers"][SIGNATURE_HEADER] == sign_webhook_body(webhook_secret, seen["body"])
    assert hmac_sha256_hex(webhook_secret, seen["body"]) == seen["headers"][SIGNATURE_HEADER].split("=", 1)[1]
    assert seen["headers"][EVENT_ID_HEADER] == convert.body["event_id"]

    detail = await get_event_for_request(
        env=env,
        db=db,
        headers={"Authorization": "Bearer triage-token"},
        event_id=convert.body["event_id"],
    )
    assert detail.status == 200
    assert detail.body["event"]["status"] == "delivered"


@pytest.mark.asyncio
async def test_webhook_failure_stays_pending_then_fails(env, db):
    store = EventsStore(db)
    payload = {
        "version": "ng-event-1",
        "event_type": EVENT_CONVERTED,
        "finding_id": "f-fail",
        "org_id": "org-demo",
        "dedupe_key": f"{EVENT_CONVERTED}:f-fail",
        "created_at": 1,
    }
    row, created = await store.insert_idempotent(
        event_id="evt-fail",
        org_id="org-demo",
        event_type=EVENT_CONVERTED,
        dedupe_key=payload["dedupe_key"],
        payload=payload,
        created_at_unix=1,
    )
    assert created is True

    env.NG_EVENTS_WEBHOOK_URL = "https://hooks.example/fail"
    env.NG_EVENTS_WEBHOOK_SECRET = "secret"

    async def boom(*_args, **_kwargs):
        raise RuntimeError("network down")

    for attempt in range(1, 5):
        row = await deliver_event_webhook(
            env=env, store=store, event_row=row, fetch_impl=boom,
            now=datetime.fromtimestamp(attempt, tz=timezone.utc),
        )
        assert row["status"] == "pending"
        assert row["attempts"] == attempt

    row = await deliver_event_webhook(
        env=env, store=store, event_row=row, fetch_impl=boom,
        now=datetime.fromtimestamp(5, tz=timezone.utc),
    )
    assert row["status"] == "failed"
    assert row["attempts"] == 5


@pytest.mark.asyncio
async def test_events_api_org_scoped_and_worker_route(env, db, fixture_data, secret):
    finding_id = await _ingest_one(
        env, db, fixture_data, secret, fingerprint="fp-events-api", nonce="nonce-events-4",
    )
    await convert_to_issue_for_request(
        env=env,
        db=db,
        headers={"Authorization": "Bearer triage-token"},
        finding_id=finding_id,
        new_id=_sequential_ids(),
    )

    other = await list_events_for_request(
        env=env,
        db=db,
        headers={"Authorization": "Bearer other-token"},
        query_params={},
    )
    assert other.status == 200
    assert other.body["total"] == 0

    env.DB = db
    worker = BLTWorker(env)
    response = await worker.handle_request(
        FakeRequest(
            "https://local/api/events?event_type=finding.converted",
            method="GET",
            headers={"Authorization": "Bearer triage-token"},
        ),
    )
    body = parse_json(response)
    assert response.status == 200
    assert body["total"] == 1
    assert body["events"][0]["payload"]["finding_id"] == finding_id


@pytest.mark.asyncio
async def test_emit_converted_direct_idempotent(env, db):
    finding_row = {
        "id": "f-direct",
        "org_id": "org-demo",
        "rule_id": "r1",
        "severity": "high",
        "target": "https://example.com",
        "cve_id": "CVE-2024-1",
        "cve_score": 9.1,
        "blt_issue_id": "issue-9",
    }
    first = await emit_converted_event(
        env=env, db=db, finding_row=finding_row, issue_id="issue-9", new_id=_sequential_ids(),
    )
    second = await emit_converted_event(
        env=env, db=db, finding_row=finding_row, issue_id="issue-9", new_id=_sequential_ids(),
    )
    assert first["created"] is True
    assert second["created"] is False
    assert first["event"]["id"] == second["event"]["id"]
