"""Tests for scanner coordination and dispatch behavior."""
from pathlib import Path
from types import SimpleNamespace
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from scanners.coordinator import ScannerCoordinator, register_scanner, _SCANNER_REGISTRY


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


class MissingMethodsScanner:
    """Scanner stub missing required methods."""
    pass


def make_task(task_type="crawler"):
    """Create a minimal task-like object for dispatch tests."""
    return SimpleNamespace(task_type=task_type, task_id="task-1", target_id="target-1")


@pytest.mark.asyncio
async def test_process_task_dispatches_to_scanner_by_task_type():
    coordinator = ScannerCoordinator()
    scanner = FakeScanner(scan_result={"scanner": "fake"})
    coordinator.scanner_map = {"crawler": scanner}
    result = await coordinator.process_task(make_task("crawler"))
    assert result == {"success": True, "result": {"scanner": "fake"}}
    assert len(scanner.scan_calls) == 1


@pytest.mark.asyncio
async def test_process_task_returns_error_for_unknown_task_type():
    coordinator = ScannerCoordinator()
    coordinator.scanner_map = {}
    result = await coordinator.process_task(make_task("missing"))
    assert result["success"] is False
    assert "No scanner available for task type: missing" == result["error"]


@pytest.mark.asyncio
async def test_process_task_wraps_scanner_exception():
    coordinator = ScannerCoordinator()
    coordinator.scanner_map = {"crawler": FakeScanner(should_raise=True)}
    result = await coordinator.process_task(make_task("crawler"))
    assert result["success"] is False
    assert result["error"] == "scan failed"


@pytest.mark.asyncio
async def test_get_all_scanner_status_aggregates_each_scanner():
    coordinator = ScannerCoordinator()
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


def test_init_populates_scanner_map_from_registry():
    """__init__ must build scanner_map from _SCANNER_REGISTRY."""
    coordinator = ScannerCoordinator()
    assert set(coordinator.scanner_map.keys()) == set(_SCANNER_REGISTRY.keys())


def test_register_scanner_raises_on_empty_task_type():
    with pytest.raises(ValueError, match="non-empty string"):
        register_scanner('', FakeScanner)


def test_register_scanner_raises_on_duplicate_task_type():
    with pytest.raises(ValueError, match="already registered"):
        register_scanner('crawler', FakeScanner)


def test_register_scanner_raises_on_missing_scan_method():
    with pytest.raises(TypeError, match="must define `scan`"):
        register_scanner('unique_type_scan', MissingMethodsScanner)


def test_register_scanner_raises_on_missing_get_status_method():
    class OnlyScan:
        async def scan(self, task):
            pass

    with pytest.raises(TypeError, match="must define `get_status`"):
        register_scanner('unique_type_status', OnlyScan)


@pytest.mark.asyncio
async def test_process_job_returns_all_results():
    """process_job must collect and return results for all tasks."""
    coordinator = ScannerCoordinator()
    scanner = FakeScanner(scan_result={"data": 1})
    coordinator.scanner_map = {"crawler": scanner}
    tasks = [make_task("crawler"), make_task("crawler")]
    results = await coordinator.process_job("job-1", tasks)
    assert len(results) == 2
    assert all(r["success"] is True for r in results)
