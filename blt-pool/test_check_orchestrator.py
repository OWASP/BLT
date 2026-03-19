"""Unit tests for src/services/check_orchestrator.py."""

import asyncio
import json
import pathlib
import sys

_SRC_PATH = pathlib.Path(__file__).parent / "src"
sys.path.insert(0, str(_SRC_PATH))

from services.check_orchestrator import (  # noqa: E402
    build_check_dispatch_requests,
    dispatch_check_orchestrator_event,
    should_dispatch_check_orchestrator_event,
)


class _Resp:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self._payload = payload

    async def text(self):
        return json.dumps(self._payload)


def _run(coro):
    return asyncio.run(coro)


def test_should_dispatch_check_orchestrator_event_matrix():
    assert should_dispatch_check_orchestrator_event("pull_request", "opened")
    assert should_dispatch_check_orchestrator_event("pull_request", "synchronize")
    assert should_dispatch_check_orchestrator_event("pull_request", "reopened")
    assert should_dispatch_check_orchestrator_event("check_suite", "rerequested")

    assert not should_dispatch_check_orchestrator_event("pull_request", "closed")
    assert not should_dispatch_check_orchestrator_event("check_suite", "requested")
    assert not should_dispatch_check_orchestrator_event("issues", "opened")


def test_build_check_dispatch_requests_from_pull_request():
    payload = {
        "repository": {"owner": {"login": "OWASP-BLT"}, "name": "BLT-GitHub-App"},
        "pull_request": {
            "number": 101,
            "html_url": "https://github.com/OWASP-BLT/BLT-GitHub-App/pull/101",
            "head": {"sha": "abc123"},
        },
    }
    requests = build_check_dispatch_requests("pull_request", "opened", payload)
    assert len(requests) == 1
    assert requests[0]["owner"] == "OWASP-BLT"
    assert requests[0]["repo"] == "BLT-GitHub-App"
    assert requests[0]["pr_number"] == 101
    assert requests[0]["head_sha"] == "abc123"


def test_build_check_dispatch_requests_from_check_suite_rerequested():
    payload = {
        "repository": {"owner": {"login": "OWASP-BLT"}, "name": "BLT-GitHub-App"},
        "check_suite": {
            "head_sha": "def456",
            "pull_requests": [{"number": 11}, {"number": 12}],
        },
    }
    requests = build_check_dispatch_requests("check_suite", "rerequested", payload)
    assert len(requests) == 2
    assert {r["pr_number"] for r in requests} == {11, 12}
    assert all(r["head_sha"] == "def456" for r in requests)


def test_dispatch_check_orchestrator_event_posts_and_completes_runs():
    payload = {
        "repository": {"owner": {"login": "OWASP-BLT"}, "name": "BLT-GitHub-App"},
        "pull_request": {
            "number": 101,
            "html_url": "https://github.com/OWASP-BLT/BLT-GitHub-App/pull/101",
            "head": {"sha": "abc123"},
        },
    }
    calls = []

    async def fake_github_api(method, path, token, body=None):
        calls.append((method, path, token, body))
        if method == "POST":
            return _Resp(201, {"id": 9001})
        return _Resp(200, {})

    dispatched = _run(
        dispatch_check_orchestrator_event(
            "pull_request",
            "opened",
            payload,
            "tok",
            fake_github_api,
        )
    )

    assert dispatched == 1
    assert len(calls) == 2
    assert calls[0][0] == "POST"
    assert calls[0][1] == "/repos/OWASP-BLT/BLT-GitHub-App/check-runs"
    assert calls[1][0] == "PATCH"
    assert calls[1][1] == "/repos/OWASP-BLT/BLT-GitHub-App/check-runs/9001"
    assert calls[1][3]["status"] == "completed"


def test_dispatch_check_orchestrator_event_skips_when_suite_not_linked_to_prs():
    payload = {
        "repository": {"owner": {"login": "OWASP-BLT"}, "name": "BLT-GitHub-App"},
        "check_suite": {
            "head_sha": "def456",
            "pull_requests": [],
        },
    }

    async def fake_github_api(method, path, token, body=None):
        raise AssertionError("github_api should not be called when no dispatch requests exist")

    dispatched = _run(
        dispatch_check_orchestrator_event(
            "check_suite",
            "rerequested",
            payload,
            "tok",
            fake_github_api,
        )
    )

    assert dispatched == 0
