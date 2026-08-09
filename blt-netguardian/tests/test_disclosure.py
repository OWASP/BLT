"""security.txt parser + disclosure API."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from canonicalize import body_digest_hex
from disclosure import parse_security_txt, security_txt_urls, target_origin
from envelope import prepare_signed_envelope
from findings_service import disclosure_for_request
from ingest_service import process_ingest
from ingest_store import IngestStore
from netguardian_db import open_netguardian_db

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "canonical_vectors.json"

SAMPLE = """
# Comment
Contact: mailto:security@example.com
Contact: https://example.com/contact
Expires: 2027-01-01T00:00:00.000Z
Policy: https://example.com/security
Preferred-Languages: en, es
"""


def test_parse_and_urls():
    assert target_origin("example.com") == "https://example.com"
    assert security_txt_urls("https://example.com")[0].endswith("/.well-known/security.txt")
    fields = parse_security_txt(SAMPLE)
    assert fields["Contact"][0] == "mailto:security@example.com"
    assert fields["Policy"] == ["https://example.com/security"]
    assert "bogus" not in fields


@pytest.mark.asyncio
async def test_disclosure_endpoint_uses_fetch_impl():
    fixture = json.loads(FIXTURES.read_text())
    secret = bytes.fromhex(fixture["secret_hex"])
    env = SimpleNamespace(
        NG_SENDER_SECRETS=json.dumps({"org-demo:scanner-1:k1": fixture["secret_hex"]}),
        NG_ORG_API_TOKENS=json.dumps({"triage-token": "org-demo"}),
        NG_INGEST_RPM="60",
    )
    db = open_netguardian_db(REPO_ROOT)
    try:
        body = dict(fixture["envelope_unsigned"])
        body.pop("payload_digest", None)
        body["nonce"] = "disclosure-nonce-1"
        body["issued_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        body["payload_plaintext"]["fingerprint"] = "fp-disclosure"
        body["payload_plaintext"]["target"] = "https://example.com/app"
        signed = prepare_signed_envelope(body, secret)
        raw = json.dumps(signed, separators=(",", ":"), ensure_ascii=False).encode()
        ingest = await process_ingest(
            raw_body=raw,
            body_digest_header=f"sha256={body_digest_hex(raw)}",
            envelope=signed,
            env=env,
            db=db,
            store=IngestStore(db),
            new_id=lambda p: f"{p}-d",
        )
        assert ingest.status == 201

        async def fake_fetch(url: str):
            assert url.endswith("/.well-known/security.txt")
            return 200, SAMPLE

        result = await disclosure_for_request(
            env=env,
            db=db,
            headers={"Authorization": "Bearer triage-token"},
            finding_id=ingest.body["finding_id"],
            fetch_impl=fake_fetch,
        )
        assert result.status == 200
        disc = result.body["disclosure"]
        assert disc["found"] is True
        assert disc["contacts"][0] == "mailto:security@example.com"
        assert "mailto:security@example.com" in disc["convert_hint"]
    finally:
        db.conn.close()
