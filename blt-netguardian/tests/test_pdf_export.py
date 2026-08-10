"""PDF export: Workers-safe renderer + redaction snapshot tests."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from canonicalize import body_digest_hex
from envelope import prepare_signed_envelope
from findings_service import export_finding_pdf_for_request, export_pdf_for_request
from ingest_service import process_ingest
from ingest_store import IngestStore
from netguardian_db import open_netguardian_db
from pdf_report import (
    build_findings_pdf,
    pdf_contains_plaintext_secret,
    presentation_finding,
    render_pdf,
    sanitize_target,
)
from test_worker_api import BLTWorker, FakeRequest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "canonical_vectors.json"

SECRET_PLAIN = "super-secret-token-value-xyz"


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
        NG_ORG_API_TOKENS=json.dumps({"triage-token": "org-demo"}),
        NG_INGEST_RPM="60",
        AUTHENTICATE_READ_ENDPOINTS="false",
        NG_DEFAULT_ORG="org-demo",
    )


@pytest.fixture
def db():
    db = open_netguardian_db(REPO_ROOT)
    yield db
    db.conn.close()


def test_render_pdf_is_valid_header():
    pdf = render_pdf(["NetGuardian", "line two"])
    assert pdf.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf
    assert b"NetGuardian" in pdf


def test_redacted_snippet_never_leaks_secret_literals():
    finding = {
        "id": "f1",
        "org_id": "org-demo",
        "rule_id": "http.missing-hsts",
        "severity": "high",
        "title": "Missing HSTS",
        "target": "https://example.com",
        "status": "open",
        "cve_id": None,
        "cve_score": None,
    }
    snippet = {"token": SECRET_PLAIN, "note": "visible", "password": "hunter2"}
    pdf = build_findings_pdf(
        [finding],
        org_id="org-demo",
        snippet_by_id={"f1": snippet},
    )
    leaked = pdf_contains_plaintext_secret(pdf, [SECRET_PLAIN, "hunter2"])
    assert leaked == []
    assert b"[REDACTED]" in pdf
    assert b"visible" in pdf


def test_sanitize_target_strips_credentials_query_and_fragment():
    assert (
        sanitize_target(f"https://user:pass@example.com/a/b?token={SECRET_PLAIN}#frag")
        == "https://example.com/a/b"
    )


def test_metadata_redaction_keeps_secret_plain_out_of_pdf():
    finding = {
        "id": "f-meta",
        "org_id": "org-demo",
        "rule_id": "http.missing-hsts",
        "severity": "high",
        "title": f"Leak token={SECRET_PLAIN} in title",
        "target": f"https://user:{SECRET_PLAIN}@example.com/path?api_key={SECRET_PLAIN}#x",
        "fingerprint": f"token={SECRET_PLAIN}",
        "status": "open",
        "cve_id": None,
        "cve_score": None,
    }
    safe = presentation_finding(finding)
    assert SECRET_PLAIN not in safe["title"]
    assert SECRET_PLAIN not in safe["target"]
    assert SECRET_PLAIN not in safe["fingerprint"]
    assert safe["target"] == "https://example.com/path"
    assert "token=[REDACTED]" in safe["title"]

    pdf = build_findings_pdf([finding], org_id="org-demo")
    assert pdf_contains_plaintext_secret(pdf, [SECRET_PLAIN]) == []
    assert b"https://example.com/path" in pdf
    assert b"token=[REDACTED]" in pdf


@pytest.mark.asyncio
async def test_export_pdf_list_and_detail(env, db, fixture_data, secret):
    body = dict(fixture_data["envelope_unsigned"])
    body.pop("payload_digest", None)
    body["nonce"] = "pdf-nonce-1"
    body["issued_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body["payload_plaintext"]["fingerprint"] = "fp-pdf-1"
    body["payload_plaintext"]["token"] = SECRET_PLAIN
    body["payload_plaintext"]["title"] = "PDF test finding"
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
    finding_id = ingest.body["finding_id"]
    headers = {"Authorization": "Bearer triage-token"}

    listed = await export_pdf_for_request(
        env=env, db=db, headers=headers, query_params={},
    )
    assert listed.status == 200
    assert listed.content_type == "application/pdf"
    assert listed.body["pdf"].startswith(b"%PDF-1.4")
    # List export must not embed evidence secrets
    assert pdf_contains_plaintext_secret(listed.body["pdf"], [SECRET_PLAIN]) == []

    detail = await export_finding_pdf_for_request(
        env=env,
        db=db,
        headers=headers,
        finding_id=finding_id,
        new_id=_sequential_ids(),
    )
    assert detail.status == 200
    pdf = detail.body["pdf"]
    assert pdf.startswith(b"%PDF-1.4")
    assert pdf_contains_plaintext_secret(pdf, [SECRET_PLAIN]) == []
    assert b"[REDACTED]" in pdf
    assert finding_id.encode("latin-1") in pdf


@pytest.mark.asyncio
async def test_worker_export_pdf_route(env, db, fixture_data, secret):
    body = dict(fixture_data["envelope_unsigned"])
    body.pop("payload_digest", None)
    body["nonce"] = "pdf-nonce-2"
    body["issued_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body["payload_plaintext"]["fingerprint"] = "fp-pdf-2"
    signed = prepare_signed_envelope(body, secret)
    raw = json.dumps(signed, separators=(",", ":"), ensure_ascii=False).encode()
    await process_ingest(
        raw_body=raw,
        body_digest_header=f"sha256={body_digest_hex(raw)}",
        envelope=signed,
        env=env,
        db=db,
        store=IngestStore(db),
        new_id=_sequential_ids(),
    )

    env.DB = db
    worker = BLTWorker(env)
    response = await worker.handle_request(
        FakeRequest(
            "https://local/api/findings/export.pdf",
            method="GET",
            headers={"Authorization": "Bearer triage-token"},
        )
    )
    assert response.status == 200
    assert response.headers["Content-Type"] == "application/pdf"
    assert isinstance(response.body, (bytes, bytearray))
    assert response.body.startswith(b"%PDF-1.4")
