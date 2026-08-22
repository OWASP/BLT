"""Shared domain queue: submit, claim lease, complete, fail, expire."""

from pathlib import Path
import json
import sys
import types
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

if "workers" not in sys.modules:
    workers_module = types.ModuleType("workers")

    class FakeResponse:
        def __init__(self, body="", status=200, headers=None):
            self.body = body
            self.status = status
            self.headers = dict(headers or {})

    workers_module.Response = FakeResponse
    sys.modules["workers"] = workers_module

from netguardian_db import open_netguardian_db  # noqa: E402
from worker import BLTWorker  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


class FakeRequest:
    def __init__(self, url, method="GET", payload=None, headers=None):
        self.url = url
        self.method = method
        self.headers = dict(headers or {})
        if payload is None:
            self._body = b""
        else:
            self._body = json.dumps(payload).encode()
        self.body = self._body

    async def json(self):
        return json.loads(self._body.decode())

    async def text(self):
        return self._body.decode()


def parse(response):
    return json.loads(response.body)


def env_with_db():
    db = open_netguardian_db(REPO)
    return SimpleNamespace(
        DB=db,
        AUTHENTICATE_READ_ENDPOINTS="false",
        NG_DEFAULT_ORG="org-demo",
        NG_ORG_API_TOKENS=json.dumps({"triage-token": "org-demo"}),
        CORS_ALLOWED_ORIGINS="http://localhost:8888",
    ), db


@pytest.mark.asyncio
async def test_submit_claim_complete_flow():
    env, _db = env_with_db()
    worker = BLTWorker(env)

    submit = await worker.handle_request(
        FakeRequest(
            "http://127.0.0.1:8787/api/domains",
            method="POST",
            payload={
                "sender_id": "scanner-1",
                "domains": [
                    "https://WWW.Example.com/foo",
                    "http://example.com/",
                    "https://other.test/",
                ],
                "source_url": "https://seed.test/",
            },
        )
    )
    body = parse(submit)
    assert submit.status == 200
    assert len(body["created"]) == 2
    assert "example.com" in body["duplicate_hosts"] or len(body["duplicate_hosts"]) == 1

    listed = parse(
        await worker.handle_request(FakeRequest("http://127.0.0.1:8787/api/domains"))
    )
    assert listed["counts"]["pending"] == 2

    first = parse(
        await worker.handle_request(
            FakeRequest(
                "http://127.0.0.1:8787/api/domains/claim",
                method="POST",
                payload={"sender_id": "scanner-1"},
            )
        )
    )
    job = first["job"]
    assert job["status"] == "in_progress"
    assert job["claimed_by"] == "scanner-1"
    assert job["host_key"] in {"example.com", "other.test"}

    second = parse(
        await worker.handle_request(
            FakeRequest(
                "http://127.0.0.1:8787/api/domains/claim",
                method="POST",
                payload={"sender_id": "scanner-2"},
            )
        )
    )
    assert second["job"]["id"] != job["id"]
    assert second["job"]["claimed_by"] == "scanner-2"

    done = parse(
        await worker.handle_request(
            FakeRequest(
                f"http://127.0.0.1:8787/api/domains/{job['id']}/complete",
                method="POST",
                payload={
                    "sender_id": "scanner-1",
                    "result": {"pages": 3, "discovered_hosts": ["iana.org"]},
                },
            )
        )
    )
    assert done["job"]["status"] == "scanned"
    assert done["job"]["result"]["pages"] == 3

    empty = parse(
        await worker.handle_request(
            FakeRequest(
                "http://127.0.0.1:8787/api/domains/claim",
                method="POST",
                payload={"sender_id": "scanner-3"},
            )
        )
    )
    # one job still in_progress (scanner-2), none pending
    assert empty["job"] is None or empty["job"]["id"] == second["job"]["id"]


@pytest.mark.asyncio
async def test_fail_marks_retry_then_lease_expire():
    env, db = env_with_db()
    worker = BLTWorker(env)
    await worker.handle_request(
        FakeRequest(
            "http://127.0.0.1:8787/api/domains",
            method="POST",
            payload={"domains": ["https://fail.test/"], "sender_id": "a"},
        )
    )
    claimed = parse(
        await worker.handle_request(
            FakeRequest(
                "http://127.0.0.1:8787/api/domains/claim",
                method="POST",
                payload={"sender_id": "a"},
            )
        )
    )
    job_id = claimed["job"]["id"]
    failed = parse(
        await worker.handle_request(
            FakeRequest(
                f"http://127.0.0.1:8787/api/domains/{job_id}/fail",
                method="POST",
                payload={"sender_id": "a", "error": "timeout"},
            )
        )
    )
    assert failed["job"]["status"] == "retry_required"
    assert failed["job"]["retry_count"] == 1

    from domain_queue_store import DomainQueueStore

    store = DomainQueueStore(db)
    # Simulate abandoned in-progress lease
    rec = parse(
        await worker.handle_request(
            FakeRequest(
                "http://127.0.0.1:8787/api/domains/claim",
                method="POST",
                payload={"sender_id": "b"},
            )
        )
    )
    assert rec["job"]["status"] == "in_progress"
    expired = await store.expire_stale(9_999_999_999)
    assert expired >= 1
    again = parse(
        await worker.handle_request(
            FakeRequest(
                "http://127.0.0.1:8787/api/domains/claim",
                method="POST",
                payload={"sender_id": "c"},
            )
        )
    )
    assert again["job"]["host_key"] == "fail.test"
    assert again["job"]["claimed_by"] == "c"


@pytest.mark.asyncio
async def test_heartbeat_extends_lease():
    env, _db = env_with_db()
    worker = BLTWorker(env)
    await worker.handle_request(
        FakeRequest(
            "http://127.0.0.1:8787/api/domains",
            method="POST",
            payload={"domains": ["https://beat.test/"], "sender_id": "a"},
        )
    )
    claimed = parse(
        await worker.handle_request(
            FakeRequest(
                "http://127.0.0.1:8787/api/domains/claim",
                method="POST",
                payload={"sender_id": "a"},
            )
        )
    )
    job_id = claimed["job"]["id"]
    until = claimed["job"]["claim_until"]
    beat = parse(
        await worker.handle_request(
            FakeRequest(
                f"http://127.0.0.1:8787/api/domains/{job_id}/heartbeat",
                method="POST",
                payload={"sender_id": "a"},
            )
        )
    )
    assert beat["job"]["status"] == "in_progress"
    assert beat["job"]["claim_until"] >= until

