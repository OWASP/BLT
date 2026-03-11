"""API handler tests for BLTWorker."""
from pathlib import Path
import json
import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


class FakeResponse:
    """Minimal workers.Response-compatible object for tests."""

    def __init__(self, body="", status=200, headers=None):
        self.body = body
        self.status = status
        self.headers = dict(headers or {})


if "workers" not in sys.modules:
    workers_module = types.ModuleType("workers")
    workers_module.Response = FakeResponse
    sys.modules["workers"] = workers_module

from worker import BLTWorker, on_fetch  # noqa: E402


class FakeRequest:
    """Minimal request object for worker handler tests."""

    def __init__(self, url, method="GET", payload=None):
        self.url = url
        self.method = method
        self._payload = payload

    async def json(self):
        return self._payload or {}


def parse_json(response):
    """Parse a JSON response body from BLTWorker handlers."""
    return json.loads(response.body)


@pytest.mark.asyncio
async def test_handle_request_options_returns_cors_headers():
    worker = BLTWorker(SimpleNamespace(DB=None))

    response = await worker.handle_request(
        FakeRequest("https://api.example.com/api/tasks/queue", method="OPTIONS")
    )

    assert response.status == 200
    assert response.body == ""
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert "GET, POST, PUT, DELETE, OPTIONS" in response.headers["Access-Control-Allow-Methods"]


@pytest.mark.asyncio
async def test_handle_request_root_returns_404_without_assets():
    """When no ASSETS binding is present (e.g. in tests) the worker returns 404
    for the root path; in production the ASSETS binding intercepts it first."""
    worker = BLTWorker(SimpleNamespace(DB=None))

    response = await worker.handle_request(FakeRequest("https://api.example.com/"))
    payload = parse_json(response)

    assert response.status == 404
    assert payload["error"] == "Not found"


@pytest.mark.asyncio
async def test_handle_request_unknown_path_returns_404():
    worker = BLTWorker(SimpleNamespace(DB=None))

    response = await worker.handle_request(FakeRequest("https://api.example.com/no-such-route"))
    payload = parse_json(response)

    assert response.status == 404
    assert payload["error"] == "Not found"


@pytest.mark.asyncio
async def test_handle_task_queue_rejects_non_post():
    worker = BLTWorker(SimpleNamespace(DB=None))

    response = await worker.handle_task_queue(
        FakeRequest("https://api.example.com/api/tasks/queue", method="GET")
    )
    payload = parse_json(response)

    assert response.status == 405
    assert payload["error"] == "Method not allowed"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload, expected_fields",
    [
        ({}, "target_id, task_types"),
        ({"target_id": "target-1"}, "task_types"),
        ({"task_types": ["crawler"]}, "target_id"),
    ],
)
async def test_handle_task_queue_validates_required_fields(payload, expected_fields):
    worker = BLTWorker(SimpleNamespace(DB=None))

    response = await worker.handle_task_queue(
        FakeRequest(
            "https://api.example.com/api/tasks/queue",
            method="POST",
            payload=payload,
        )
    )
    payload = parse_json(response)

    assert response.status == 400
    assert payload["error"] == f"Missing required fields: {expected_fields}"


@pytest.mark.asyncio
async def test_handle_task_queue_tracks_deduplicated_tasks():
    worker = BLTWorker(SimpleNamespace(DB=None))
    worker.deduplicator = SimpleNamespace(
        is_duplicate=AsyncMock(side_effect=[False, True])
    )
    worker.task_queue = SimpleNamespace(save_task=AsyncMock())
    worker.job_store = SimpleNamespace(save_job=AsyncMock())
    worker.coordinator = SimpleNamespace(process_job=AsyncMock())

    response = await worker.handle_task_queue(
        FakeRequest(
            "https://api.example.com/api/tasks/queue",
            method="POST",
            payload={
                "target_id": "target-1",
                "task_types": ["crawler", "static_analysis"],
                "priority": "high",
            },
        )
    )
    payload = parse_json(response)

    assert response.status == 200
    assert payload["success"] is True
    assert payload["tasks_queued"] == 1
    assert payload["tasks_deduplicated"] == 1
    assert worker.deduplicator.is_duplicate.await_count == 2
    worker.task_queue.save_task.assert_awaited_once()
    worker.job_store.save_job.assert_awaited_once()
    worker.coordinator.process_job.assert_awaited_once()

    _, queued_tasks = worker.coordinator.process_job.await_args.args
    assert len(queued_tasks) == 1
    assert queued_tasks[0].task_type == "crawler"


@pytest.mark.asyncio
async def test_handle_target_registration_persists_target():
    worker = BLTWorker(SimpleNamespace(DB=None))
    worker.target_registry = SimpleNamespace(save_target=AsyncMock())

    response = await worker.handle_target_registration(
        FakeRequest(
            "https://api.example.com/api/targets/register",
            method="POST",
            payload={
                "target_type": "web2",
                "target": "https://example.com",
                "scan_types": ["crawler"],
                "notes": "focus auth",
            },
        )
    )
    payload = parse_json(response)
    saved_target = worker.target_registry.save_target.await_args.args[0]

    assert response.status == 200
    assert payload["success"] is True
    assert payload["message"] == "Target registered successfully"
    assert saved_target["target_type"] == "web2"
    assert saved_target["target_url"] == "https://example.com"
    assert saved_target["scan_types"] == ["crawler"]


@pytest.mark.asyncio
async def test_handle_result_ingestion_updates_state_and_notifies():
    worker = BLTWorker(SimpleNamespace(DB=None))
    worker.vuln_db = SimpleNamespace(store_vulnerability=AsyncMock())
    worker.task_queue = SimpleNamespace(
        get_task=AsyncMock(return_value={"job_id": "job-1", "target_id": "target-1"}),
        update_task=AsyncMock(),
    )
    worker.job_store = SimpleNamespace(update_job_progress=AsyncMock())
    worker.target_registry = SimpleNamespace(
        get_target=AsyncMock(return_value={"target_url": "https://example.com"})
    )
    worker.notifier = SimpleNamespace(
        notify_vulnerability=AsyncMock(return_value={"successful_contacts": 2})
    )

    response = await worker.handle_result_ingestion(
        FakeRequest(
            "https://api.example.com/api/results/ingest",
            method="POST",
            payload={
                "task_id": "task-1",
                "agent_type": "static_analyzer",
                "results": {
                    "findings": [{"type": "check"}],
                    "vulnerabilities": [
                        {
                            "type": "xss",
                            "severity": "high",
                            "title": "Reflected XSS",
                            "affected_component": "/search",
                        }
                    ],
                },
            },
        )
    )
    payload = parse_json(response)

    assert response.status == 200
    assert payload["success"] is True
    assert payload["vulnerabilities_found"] == 1
    assert payload["contact_attempted"] is True
    assert payload["contact_successful"] == 2
    assert worker.vuln_db.store_vulnerability.await_count == 1
    worker.task_queue.update_task.assert_awaited_once()
    worker.job_store.update_job_progress.assert_awaited_once_with("job-1")
    assert worker.notifier.notify_vulnerability.await_args.kwargs["target"] == "https://example.com"


@pytest.mark.asyncio
async def test_handle_job_status_validates_query_param():
    worker = BLTWorker(SimpleNamespace(DB=None))

    response = await worker.handle_job_status(
        FakeRequest("https://api.example.com/api/jobs/status")
    )
    payload = parse_json(response)

    assert response.status == 400
    assert payload["error"] == "Missing job_id parameter"


@pytest.mark.asyncio
async def test_handle_job_status_calculates_progress_percentage():
    worker = BLTWorker(SimpleNamespace(DB=None))
    worker.job_store = SimpleNamespace(
        get_job=AsyncMock(
            return_value={
                "job_id": "job-1",
                "status": "running",
                "total_tasks": 4,
                "completed_tasks": 1,
                "created_at": "2026-01-01T00:00:00",
                "updated_at": "2026-01-01T00:01:00",
            }
        )
    )

    response = await worker.handle_job_status(
        FakeRequest("https://api.example.com/api/jobs/status?job_id=job-1")
    )
    payload = parse_json(response)

    assert response.status == 200
    assert payload["job_id"] == "job-1"
    assert payload["progress"] == 25


@pytest.mark.asyncio
async def test_handle_task_list_returns_existing_tasks_only():
    worker = BLTWorker(SimpleNamespace(DB=None))
    worker.job_store = SimpleNamespace(
        get_job=AsyncMock(return_value={"task_ids": ["task-a", "task-b"]})
    )
    worker.task_queue = SimpleNamespace(
        get_task=AsyncMock(side_effect=[{"task_id": "task-a"}, None])
    )

    response = await worker.handle_task_list(
        FakeRequest("https://api.example.com/api/tasks/list?job_id=job-1")
    )
    payload = parse_json(response)

    assert response.status == 200
    assert payload["job_id"] == "job-1"
    assert payload["tasks"] == [{"task_id": "task-a"}]
    assert worker.task_queue.get_task.await_count == 2


@pytest.mark.asyncio
async def test_handle_vulnerabilities_passes_limit_and_severity():
    worker = BLTWorker(SimpleNamespace(DB=None))
    worker.vuln_db = SimpleNamespace(get_vulnerabilities=AsyncMock(return_value=[{"id": 1}]))

    response = await worker.handle_vulnerabilities(
        FakeRequest("https://api.example.com/api/vulnerabilities?limit=25&severity=high")
    )
    payload = parse_json(response)

    assert response.status == 200
    assert payload == {"count": 1, "vulnerabilities": [{"id": 1}]}
    worker.vuln_db.get_vulnerabilities.assert_awaited_once_with(25, "high")


@pytest.mark.asyncio
async def test_handle_request_returns_500_when_handler_raises():
    worker = BLTWorker(SimpleNamespace(DB=None))
    worker.handle_vulnerabilities = AsyncMock(side_effect=RuntimeError("boom"))

    response = await worker.handle_request(
        FakeRequest("https://api.example.com/api/vulnerabilities")
    )
    payload = parse_json(response)

    assert response.status == 500
    assert payload["error"] == "Internal server error"
    assert payload["message"] == "boom"
    assert response.headers["Access-Control-Allow-Origin"] == "*"


@pytest.mark.asyncio
async def test_on_fetch_entrypoint_routes_api_requests():
    """on_fetch delegates API paths to the BLTWorker handler."""
    response = await on_fetch(
        FakeRequest("https://api.example.com/api/jobs/status"),
        SimpleNamespace(DB=None),
        None,
    )
    payload = parse_json(response)

    assert response.status == 400
    assert payload["error"] == "Missing job_id parameter"
