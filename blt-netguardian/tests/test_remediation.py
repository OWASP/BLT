"""Remediation fragment lookup and detail API enrichment."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from canonicalize import body_digest_hex
from envelope import prepare_signed_envelope
from findings_service import get_finding_for_request
from ingest_service import process_ingest
from ingest_store import IngestStore
from netguardian_db import open_netguardian_db
from remediation.fragments import lookup_remediation

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "canonical_vectors.json"


def _sequential_ids():
    counter = {"n": 0}

    def new_id(label: str) -> str:
        counter["n"] += 1
        return f"{label}-{counter['n']}"

    return new_id


def test_lookup_exact_and_prefix_and_cve():
    hsts = lookup_remediation("http.missing-hsts")
    assert "HSTS" in hsts["why"] or "Strict-Transport" in hsts["markdown"]
    assert any("owasp.org" in link for link in hsts["owasp_links"])
    assert "<script>" not in hsts["markdown"]

    sem = lookup_remediation("semgrep.python.sqli")
    assert sem["markdown"]
    assert any("code-review" in link for link in sem["owasp_links"])

    with_cve = lookup_remediation("http.missing-csp", cve_id="cve-2024-1234")
    assert with_cve["cve_links"][0].endswith("CVE-2024-1234")

    invalid = lookup_remediation("http.missing-csp", cve_id="CVE-invalid")
    assert invalid["cve_links"] == []


def test_lookup_unknown_has_safe_default():
    unknown = lookup_remediation("custom.weird-rule")
    assert "OWASP Top Ten" in unknown["markdown"]
    assert unknown["cve_links"] == []


@pytest.mark.asyncio
async def test_finding_detail_includes_remediation():
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
        body["nonce"] = "remediation-nonce-1"
        body["issued_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        body["payload_plaintext"]["fingerprint"] = "fp-remediation"
        body["payload_plaintext"]["rule_id"] = "http.missing-hsts"
        body["payload_plaintext"]["cve_id"] = "CVE-2024-9999"
        signed = prepare_signed_envelope(body, secret)
        raw = json.dumps(signed, separators=(",", ":"), ensure_ascii=False).encode()
        ingest = await process_ingest(
            raw_body=raw,
            body_digest_header=f"sha256={body_digest_hex(raw)}",
            envelope=signed,
            env=env,
            db=db,
            store=IngestStore(db),
            new_id=_sequential_ids(),
        )
        assert ingest.status == 201
        detail = await get_finding_for_request(
            env=env,
            db=db,
            headers={"Authorization": "Bearer triage-token"},
            finding_id=ingest.body["finding_id"],
            new_id=_sequential_ids(),
        )
        assert detail.status == 200
        rem = detail.body["remediation"]
        assert rem["rule_id"] == "http.missing-hsts"
        assert rem["owasp_links"]
        assert rem["cve_links"]
    finally:
        db.conn.close()
