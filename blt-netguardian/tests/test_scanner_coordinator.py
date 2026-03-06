"""Tests for scanner coordination and dispatch behavior."""
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from scanners.coordinator import ScannerCoordinator


class FakeScanner:
    """Scanner stub for coordinator tests."""

    def __init__(self, scan_result=None, should_raise=False):
        self.scan_result = scan_result or {"ok": True}
        self.should_raise = should_raise
        self.scan_calls = []
        self.status_calls = 0

    async def scan(self, task):
        self.scan_calls.append(task)
        if self.should_raise:
            raise RuntimeError("scan failed")
        return self.scan_result

    async def get_status(self):
        self.status_calls += 1
        return {"available": True}


def make_task(task_type="crawler"):
    """Create a minimal task-like object for dispatch tests."""
    return SimpleNamespace(task_type=task_type, task_id="task-1", target_id="target-1")


@pytest.mark.asyncio
async def test_process_task_dispatches_to_scanner_by_task_type():
    coordinator = ScannerCoordinator(env=SimpleNamespace())
    scanner = FakeScanner(scan_result={"scanner": "fake"})
    coordinator.scanner_map = {"crawler": scanner}

    result = await coordinator.process_task(make_task("crawler"))

    assert result == {"success": True, "result": {"scanner": "fake"}}
    assert len(scanner.scan_calls) == 1


@pytest.mark.asyncio
async def test_process_task_returns_error_for_unknown_task_type():
    coordinator = ScannerCoordinator(env=SimpleNamespace())
    coordinator.scanner_map = {}

    result = await coordinator.process_task(make_task("missing"))

    assert result["success"] is False
    assert "No scanner available for task type: missing" == result["error"]


@pytest.mark.asyncio
async def test_process_task_wraps_scanner_exception():
    coordinator = ScannerCoordinator(env=SimpleNamespace())
    coordinator.scanner_map = {"crawler": FakeScanner(should_raise=True)}

    result = await coordinator.process_task(make_task("crawler"))

    assert result["success"] is False
    assert result["error"] == "scan failed"


@pytest.mark.asyncio
async def test_get_all_scanner_status_aggregates_each_scanner():
    coordinator = ScannerCoordinator(env=SimpleNamespace())
    scanner_a = FakeScanner()
    scanner_b = FakeScanner()
    coordinator.scanner_map = {
        "crawler": scanner_a,
        "web3_monitor": scanner_b,
    }

    status = await coordinator.get_all_scanner_status()

    assert status == {
        "crawler": {"available": True},
        "web3_monitor": {"available": True},
    }
    assert scanner_a.status_calls == 1
    assert scanner_b.status_calls == 1

