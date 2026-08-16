"""Evidence attachment store + API."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from evidence_service import list_evidence_for_request, put_evidence_for_request
from evidence_store import EvidenceStore
from netguardian_db import open_netguardian_db

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def db():
    db = open_netguardian_db(REPO_ROOT)
    yield db
    db.conn.close()


@pytest.fixture
def env():
    return SimpleNamespace(
        NG_ORG_API_TOKENS='{"triage-token":"org-demo"}',
        AUTHENTICATE_READ_ENDPOINTS="false",
        NG_DEFAULT_ORG="org-demo",
    )


@pytest.mark.asyncio
async def test_d1_fallback_put_and_get(db):
    db.conn.execute("PRAGMA foreign_keys=OFF")
    store = EvidenceStore(db, SimpleNamespace())
    meta = await store.put(
        evidence_id="evd-1",
        org_id="org-demo",
        finding_id="f-1",
        data=b"hello-evidence",
        media_type="text/plain",
        created_at_unix=1,
    )
    assert meta["backend"] == "d1"
    assert meta["size_bytes"] == 14
    blob = await store.get_bytes(meta)
    assert blob == b"hello-evidence"
    listed = await store.list_for_finding("org-demo", "f-1")
    assert len(listed) == 1


@pytest.mark.asyncio
async def test_put_evidence_requires_mutation_auth(env, db):
    result = await put_evidence_for_request(
        env=env,
        db=db,
        headers={},
        finding_id="missing",
        body={"data_b64": base64.b64encode(b"x").decode(), "media_type": "text/plain"},
        now=datetime.now(timezone.utc),
    )
    assert result.status == 401


@pytest.mark.asyncio
async def test_list_evidence_demo_read(env, db):
    result = await list_evidence_for_request(
        env=env,
        db=db,
        headers={},
        finding_id="missing",
    )
    assert result.status == 404
