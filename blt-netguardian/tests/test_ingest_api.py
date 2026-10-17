"""Tests for POST /api/ingest."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from canonicalize import body_digest_hex
from envelope import prepare_signed_envelope
from errors import IngestErrorCode
from ingest_service import process_ingest
from ingest_store import IngestStore
from test_storage import FakeDB, FakePreparedStatement  # noqa: F401 — re-export for ingest fake

FIXTURES = Path(__file__).parent / "fixtures" / "canonical_vectors.json"


class IngestFakeDB(FakeDB):
    """D1 fake with in-memory envelope nonce index for ingest tests."""

    def __init__(self, *, sender_active: int = 1, rate_count: int = 0):
        super().__init__()
        self.envelopes = {}
        self.sender_active = sender_active
        # Default count for any bucket not yet written (used by RPM tests).
        self.rate_count = rate_count
        self.metrics: dict[str, int] = {}
        self.inserts = []

    def prepare(self, sql):
        self.prepare_calls.append(sql)
        return IngestPreparedStatement(self, sql)

    async def batch(self, statements):
        results = []
        for stmt in statements:
            results.append(await stmt.run())
        return results


class IngestPreparedStatement(FakePreparedStatement):
    async def first(self):
        self.db.first_calls.append((self.sql, self.params))
        sql = self.sql.lower()
        if "from sender_keys" in sql:
            if self.db.sender_active is None:
                return None
            return {"active": self.db.sender_active}
        if "from envelopes" in sql and "nonce" in sql:
            org_id, sender_id, nonce = self.params
            key = (org_id, sender_id, nonce)
            row = self.db.envelopes.get(key)
            if row:
                return {"id": row["envelope_id"], "finding_id": row["finding_id"]}
            return None
        if "from ng_metrics" in sql:
            bucket = self.params[1]
            count = self.db.metrics.get(bucket, self.db.rate_count)
            return {"ingest_accepted": count}
        return None

    async def run(self):
        self.db.run_calls.append((self.sql, self.params))
        sql = self.sql.lower()
        if sql.strip().startswith("insert into envelopes"):
            self.db.inserts.append(("envelope", self.params))
        elif sql.strip().startswith("insert into findings"):
            self.db.inserts.append(("finding", self.params))
        elif "update envelopes set finding_id" in sql:
            for row in self.db.envelopes.values():
                if row["envelope_id"] == self.params[1]:
                    row["finding_id"] = self.params[0]
        elif "insert into ng_metrics" in sql:
            bucket = self.params[1]
            self.db.metrics[bucket] = self.db.metrics.get(bucket, self.db.rate_count) + 1
        return {}


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
        NG_INGEST_RPM="60",
        NG_INGEST_RPH="1000",
    )


@pytest.fixture
def signed_envelope(fixture_data, secret):
    env_body = dict(fixture_data["envelope_unsigned"])
    env_body.pop("payload_digest", None)
    env_body["issued_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return prepare_signed_envelope(env_body, secret)


def _digest_header(body: bytes) -> str:
    return f"sha256={body_digest_hex(body)}"


@pytest.mark.asyncio
async def test_process_ingest_creates_finding(env, signed_envelope):
    body = json.dumps(signed_envelope, separators=(",", ":"), ensure_ascii=False).encode()
    db = IngestFakeDB(sender_active=1)
    now = datetime.now(timezone.utc)

    result = await process_ingest(
        raw_body=body,
        body_digest_header=_digest_header(body),
        envelope=signed_envelope,
        env=env,
        db=db,
        store=IngestStore(db),
        now=now,
        new_id=lambda label: f"{label}-test-id",
    )

    assert result.status == 201
    assert result.body["status"] == "created"
    assert result.body["finding_id"] == "fnd-test-id"
    assert result.body["replay"] is False
    assert any(kind == "envelope" for kind, _ in db.inserts)
    assert any(kind == "finding" for kind, _ in db.inserts)


@pytest.mark.asyncio
async def test_process_ingest_duplicate_nonce(env, signed_envelope):
    body = json.dumps(signed_envelope, separators=(",", ":"), ensure_ascii=False).encode()
    db = IngestFakeDB()
    db.envelopes[("org-demo", "scanner-1", signed_envelope["nonce"])] = {
        "envelope_id": "env-old",
        "finding_id": "fnd-old",
    }

    result = await process_ingest(
        raw_body=body,
        body_digest_header=_digest_header(body),
        envelope=signed_envelope,
        env=env,
        db=db,
        store=IngestStore(db),
    )

    assert result.status == 200
    assert result.body["status"] == "duplicate"
    assert result.body["finding_id"] == "fnd-old"
    assert result.body["replay"] is True


@pytest.mark.asyncio
async def test_process_ingest_bad_signature(env, signed_envelope):
    body_dict = dict(signed_envelope)
    body_dict["signature"] = "0" * 64
    body = json.dumps(body_dict, separators=(",", ":"), ensure_ascii=False).encode()
    db = IngestFakeDB()

    with pytest.raises(Exception) as exc_info:
        await process_ingest(
            raw_body=body,
            body_digest_header=_digest_header(body),
            envelope=body_dict,
            env=env,
            db=db,
            store=IngestStore(db),
        )
    assert exc_info.value.code == IngestErrorCode.BAD_SIGNATURE


@pytest.mark.asyncio
async def test_process_ingest_rate_limited(env, signed_envelope):
    body = json.dumps(signed_envelope, separators=(",", ":"), ensure_ascii=False).encode()
    db = IngestFakeDB()
    db.rate_count = 60
    env.NG_INGEST_RPM = "60"

    result = await process_ingest(
        raw_body=body,
        body_digest_header=_digest_header(body),
        envelope=signed_envelope,
        env=env,
        db=db,
        store=IngestStore(db),
    )

    assert result.status == 429
    assert result.body["error"] == "rate_limited"
    assert result.body["scope"] == "minute"
    assert result.headers.get("Retry-After") == "60"


@pytest.mark.asyncio
async def test_process_ingest_hour_quota_exceeded(env, fixture_data, secret):
    now = datetime(2026, 7, 20, 14, 30, 0, tzinfo=timezone.utc)
    envelope = dict(fixture_data["envelope_unsigned"])
    envelope.pop("payload_digest", None)
    envelope["issued_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    envelope["nonce"] = "hour-quota-nonce-1"
    signed = prepare_signed_envelope(envelope, secret, now=now)
    body = json.dumps(signed, separators=(",", ":"), ensure_ascii=False).encode()

    db = IngestFakeDB()
    # Under per-minute, over per-hour for the UTC hour bucket.
    db.metrics[IngestStore._hour_bucket(now)] = 1000
    env.NG_INGEST_RPM = "60"
    env.NG_INGEST_RPH = "1000"

    result = await process_ingest(
        raw_body=body,
        body_digest_header=_digest_header(body),
        envelope=signed,
        env=env,
        db=db,
        store=IngestStore(db),
        now=now,
    )

    assert result.status == 429
    assert result.body["error"] == "rate_limited"
    assert result.body["scope"] == "hour"
    # 14:30 → 15:00 = 1800 seconds
    assert result.headers.get("Retry-After") == "1800"
