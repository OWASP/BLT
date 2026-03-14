"""Tests for TaskDeduplicator, Task, ScanResult, Vulnerability, and Target models."""
import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.deduplication import TaskDeduplicator
from models.task import Task, TaskStatus, TaskType
from models.result import ScanResult, Vulnerability, VulnerabilityLevel
from models.target import Target, TargetType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeTask:
    """Minimal task-like object used only in deduplication tests."""

    def __init__(self, target_id: str, task_type: str):
        self.target_id = target_id
        self.task_type = task_type


# ===========================================================================
# TaskDeduplicator – generate_task_hash
# ===========================================================================

class TestGenerateTaskHash:
    def test_deterministic(self):
        dedup = TaskDeduplicator()
        task = _FakeTask("t1", "crawler")
        assert dedup.generate_task_hash(task) == dedup.generate_task_hash(task)

    def test_known_value(self):
        dedup = TaskDeduplicator()
        task = _FakeTask("t1", "crawler")
        expected = hashlib.sha256(b"t1:crawler").hexdigest()
        assert dedup.generate_task_hash(task) == expected

    def test_different_target_id_produces_different_hash(self):
        dedup = TaskDeduplicator()
        t1 = _FakeTask("targetA", "crawler")
        t2 = _FakeTask("targetB", "crawler")
        assert dedup.generate_task_hash(t1) != dedup.generate_task_hash(t2)

    def test_different_task_type_produces_different_hash(self):
        dedup = TaskDeduplicator()
        t1 = _FakeTask("t1", "crawler")
        t2 = _FakeTask("t1", "static_analysis")
        assert dedup.generate_task_hash(t1) != dedup.generate_task_hash(t2)

    def test_returns_hex_string(self):
        dedup = TaskDeduplicator()
        task = _FakeTask("t1", "crawler")
        h = dedup.generate_task_hash(task)
        assert isinstance(h, str)
        int(h, 16)  # raises ValueError if not valid hex


# ===========================================================================
# TaskDeduplicator – is_duplicate (cache hit / miss logic)
# ===========================================================================

class TestIsDuplicate:
    @pytest.mark.asyncio
    async def test_first_call_is_not_duplicate(self):
        dedup = TaskDeduplicator()
        task = _FakeTask("t1", "crawler")
        assert await dedup.is_duplicate(task, None) is False

    @pytest.mark.asyncio
    async def test_second_call_with_same_task_is_duplicate(self):
        dedup = TaskDeduplicator()
        task = _FakeTask("t1", "crawler")
        await dedup.is_duplicate(task, None)          # first call – caches hash
        assert await dedup.is_duplicate(task, None) is True

    @pytest.mark.asyncio
    async def test_different_tasks_are_not_duplicates_of_each_other(self):
        dedup = TaskDeduplicator()
        t1 = _FakeTask("t1", "crawler")
        t2 = _FakeTask("t2", "crawler")
        await dedup.is_duplicate(t1, None)
        assert await dedup.is_duplicate(t2, None) is False

    @pytest.mark.asyncio
    async def test_hash_added_to_seen_hashes_after_first_call(self):
        dedup = TaskDeduplicator()
        task = _FakeTask("t1", "crawler")
        assert len(dedup.seen_hashes) == 0
        await dedup.is_duplicate(task, None)
        assert len(dedup.seen_hashes) == 1

    @pytest.mark.asyncio
    async def test_multiple_unique_tasks_all_cached(self):
        dedup = TaskDeduplicator()
        for i in range(5):
            await dedup.is_duplicate(_FakeTask(f"t{i}", "crawler"), None)
        assert len(dedup.seen_hashes) == 5


# ===========================================================================
# TaskDeduplicator – clear_cache
# ===========================================================================

class TestClearCache:
    @pytest.mark.asyncio
    async def test_clear_removes_all_hashes(self):
        dedup = TaskDeduplicator()
        await dedup.is_duplicate(_FakeTask("t1", "crawler"), None)
        dedup.clear_cache()
        assert len(dedup.seen_hashes) == 0

    @pytest.mark.asyncio
    async def test_task_not_duplicate_after_cache_cleared(self):
        dedup = TaskDeduplicator()
        task = _FakeTask("t1", "crawler")
        await dedup.is_duplicate(task, None)    # marks as seen
        dedup.clear_cache()
        assert await dedup.is_duplicate(task, None) is False  # fresh start

    def test_clear_on_empty_cache_is_safe(self):
        dedup = TaskDeduplicator()
        dedup.clear_cache()  # must not raise
        assert len(dedup.seen_hashes) == 0


# ===========================================================================
# TaskStatus & TaskType enums
# ===========================================================================

class TestTaskStatusEnum:
    def test_all_values(self):
        values = {s.value for s in TaskStatus}
        assert values == {"queued", "running", "completed", "failed", "cancelled"}

    def test_is_str_subclass(self):
        assert TaskStatus.QUEUED == "queued"
        assert isinstance(TaskStatus.RUNNING, str)

    @pytest.mark.parametrize("value", ["queued", "running", "completed", "failed", "cancelled"])
    def test_construct_from_string(self, value):
        assert TaskStatus(value).value == value


class TestTaskTypeEnum:
    def test_all_values(self):
        values = {t.value for t in TaskType}
        assert values == {
            "crawler",
            "static_analysis",
            "contract_audit",
            "vulnerability_scan",
            "penetration_test",
            "web3_monitor",
        }

    def test_is_str_subclass(self):
        assert TaskType.CRAWLER == "crawler"
        assert isinstance(TaskType.WEB3_MONITOR, str)

    @pytest.mark.parametrize("value", [
        "crawler", "static_analysis", "contract_audit",
        "vulnerability_scan", "penetration_test", "web3_monitor",
    ])
    def test_construct_from_string(self, value):
        assert TaskType(value).value == value


# ===========================================================================
# Task – to_dict / from_dict round-trips
# ===========================================================================

def _make_task(**overrides) -> Task:
    base = dict(
        task_id="task-1",
        job_id="job-1",
        target_id="target-1",
        task_type=TaskType.CRAWLER,
        priority="high",
        status=TaskStatus.QUEUED,
        created_at="2026-01-01T00:00:00Z",
    )
    base.update(overrides)
    return Task(**base)


class TestTaskToDict:
    def test_required_fields_present(self):
        d = _make_task().to_dict()
        assert d["task_id"] == "task-1"
        assert d["job_id"] == "job-1"
        assert d["target_id"] == "target-1"
        assert d["priority"] == "high"
        assert d["created_at"] == "2026-01-01T00:00:00Z"

    def test_status_serialised_as_plain_string(self):
        d = _make_task(status=TaskStatus.RUNNING).to_dict()
        assert d["status"] == "running"
        assert isinstance(d["status"], str)
        assert not isinstance(d["status"], TaskStatus)

    def test_optional_fields_default_none(self):
        d = _make_task().to_dict()
        for key in ("started_at", "completed_at", "result_id", "error"):
            assert d[key] is None

    def test_optional_fields_when_set(self):
        d = _make_task(
            started_at="2026-01-01T01:00:00Z",
            completed_at="2026-01-01T02:00:00Z",
            result_id="result-99",
            error="something broke",
        ).to_dict()
        assert d["started_at"] == "2026-01-01T01:00:00Z"
        assert d["completed_at"] == "2026-01-01T02:00:00Z"
        assert d["result_id"] == "result-99"
        assert d["error"] == "something broke"


class TestTaskRoundTrip:
    def test_round_trip_minimal(self):
        original = _make_task()
        assert Task.from_dict(original.to_dict()) == original

    def test_round_trip_fully_populated(self):
        original = _make_task(
            status=TaskStatus.COMPLETED,
            started_at="2026-01-01T01:00:00Z",
            completed_at="2026-01-01T02:00:00Z",
            result_id="result-1",
            error=None,
        )
        assert Task.from_dict(original.to_dict()) == original

    def test_from_dict_restores_status_enum(self):
        data = _make_task().to_dict()
        assert Task.from_dict(data).status is TaskStatus.QUEUED

    @pytest.mark.parametrize("status", list(TaskStatus))
    def test_all_statuses_survive_round_trip(self, status):
        original = _make_task(status=status)
        assert Task.from_dict(original.to_dict()).status is status


# ===========================================================================
# VulnerabilityLevel enum
# ===========================================================================

class TestVulnerabilityLevelEnum:
    def test_all_values(self):
        values = {v.value for v in VulnerabilityLevel}
        assert values == {"critical", "high", "medium", "low", "info"}

    def test_is_str_subclass(self):
        assert VulnerabilityLevel.CRITICAL == "critical"
        assert isinstance(VulnerabilityLevel.HIGH, str)

    @pytest.mark.parametrize("value", ["critical", "high", "medium", "low", "info"])
    def test_construct_from_string(self, value):
        assert VulnerabilityLevel(value).value == value


# ===========================================================================
# Vulnerability – to_dict
# ===========================================================================

def _make_vulnerability(**overrides) -> Vulnerability:
    base = dict(
        vulnerability_id="vuln-1",
        type="sql_injection",
        severity=VulnerabilityLevel.HIGH,
        title="SQL Injection",
        description="Unsanitised input passed directly to query",
        affected_component="/api/login",
    )
    base.update(overrides)
    return Vulnerability(**base)


class TestVulnerabilityToDict:
    def test_required_fields_present(self):
        d = _make_vulnerability().to_dict()
        assert d["vulnerability_id"] == "vuln-1"
        assert d["type"] == "sql_injection"
        assert d["title"] == "SQL Injection"
        assert d["description"] == "Unsanitised input passed directly to query"
        assert d["affected_component"] == "/api/login"

    def test_severity_serialised_as_plain_string(self):
        d = _make_vulnerability(severity=VulnerabilityLevel.CRITICAL).to_dict()
        assert d["severity"] == "critical"
        assert isinstance(d["severity"], str)
        assert not isinstance(d["severity"], VulnerabilityLevel)

    def test_optional_fields_none_by_default(self):
        d = _make_vulnerability().to_dict()
        assert d["cve_id"] is None
        assert d["cvss_score"] is None
        assert d["remediation"] is None

    def test_references_defaults_to_empty_list(self):
        d = _make_vulnerability().to_dict()
        assert d["references"] == []

    def test_optional_fields_when_set(self):
        d = _make_vulnerability(
            cve_id="CVE-2021-44228",
            cvss_score=9.8,
            remediation="Update to patched version",
            references=["https://example.com/advisory"],
        ).to_dict()
        assert d["cve_id"] == "CVE-2021-44228"
        assert d["cvss_score"] == 9.8
        assert d["remediation"] == "Update to patched version"
        assert d["references"] == ["https://example.com/advisory"]

    @pytest.mark.parametrize("level", list(VulnerabilityLevel))
    def test_all_severity_levels_serialised(self, level):
        d = _make_vulnerability(severity=level).to_dict()
        assert d["severity"] == level.value


# ===========================================================================
# ScanResult – to_dict / from_dict round-trips
# ===========================================================================

def _make_scan_result(**overrides) -> ScanResult:
    base = dict(
        result_id="result-1",
        task_id="task-1",
        agent_type="crawler",
        findings=[{"url": "http://example.com", "issue": "open redirect"}],
        vulnerabilities=[{"type": "xss", "severity": "high"}],
        metadata={"pages_scanned": 42},
        timestamp="2026-01-01T00:00:00Z",
    )
    base.update(overrides)
    return ScanResult(**base)


class TestScanResultToDict:
    def test_all_fields_present(self):
        d = _make_scan_result().to_dict()
        assert d["result_id"] == "result-1"
        assert d["task_id"] == "task-1"
        assert d["agent_type"] == "crawler"
        assert d["timestamp"] == "2026-01-01T00:00:00Z"
        assert isinstance(d["findings"], list)
        assert isinstance(d["vulnerabilities"], list)
        assert isinstance(d["metadata"], dict)

    def test_findings_list_preserved(self):
        findings = [{"url": "http://a.com"}, {"url": "http://b.com"}]
        d = _make_scan_result(findings=findings).to_dict()
        assert d["findings"] == findings

    def test_empty_collections_preserved(self):
        d = _make_scan_result(findings=[], vulnerabilities=[]).to_dict()
        assert d["findings"] == []
        assert d["vulnerabilities"] == []

    def test_metadata_dict_preserved(self):
        meta = {"pages_scanned": 10, "duration_ms": 500}
        d = _make_scan_result(metadata=meta).to_dict()
        assert d["metadata"] == meta


class TestScanResultRoundTrip:
    def test_round_trip_full(self):
        original = _make_scan_result()
        assert ScanResult.from_dict(original.to_dict()) == original

    def test_round_trip_empty_collections(self):
        original = _make_scan_result(findings=[], vulnerabilities=[], metadata={})
        assert ScanResult.from_dict(original.to_dict()) == original

    def test_from_dict_defaults_optional_fields(self):
        data = {
            "result_id": "r1",
            "task_id": "t1",
            "agent_type": "crawler",
            "timestamp": "2026-01-01T00:00:00Z",
        }
        result = ScanResult.from_dict(data)
        assert result.findings == []
        assert result.vulnerabilities == []
        assert result.metadata == {}


# ===========================================================================
# TargetType enum
# ===========================================================================

class TestTargetTypeEnum:
    def test_all_values(self):
        values = {t.value for t in TargetType}
        assert values == {"web2", "web3", "api", "repo", "contract"}

    def test_is_str_subclass(self):
        assert TargetType.WEB2 == "web2"
        assert isinstance(TargetType.WEB3, str)

    @pytest.mark.parametrize("value", ["web2", "web3", "api", "repo", "contract"])
    def test_construct_from_string(self, value):
        assert TargetType(value).value == value


# ===========================================================================
# Target – to_dict / from_dict round-trips
# ===========================================================================

def _make_target(**overrides) -> Target:
    base = dict(
        target_id="target-1",
        target_type=TargetType.WEB2,
        target_url="https://example.com",
        scan_types=["crawler", "static_analysis"],
        notes="Main website",
        registered_at="2026-01-01T00:00:00Z",
    )
    base.update(overrides)
    return Target(**base)


class TestTargetToDict:
    def test_all_fields_present(self):
        d = _make_target().to_dict()
        assert d["target_id"] == "target-1"
        assert d["target_url"] == "https://example.com"
        assert d["scan_types"] == ["crawler", "static_analysis"]
        assert d["notes"] == "Main website"
        assert d["registered_at"] == "2026-01-01T00:00:00Z"

    def test_scan_types_list_preserved(self):
        types = ["crawler", "contract_audit"]
        d = _make_target(scan_types=types).to_dict()
        assert d["scan_types"] == types

    def test_empty_scan_types(self):
        d = _make_target(scan_types=[]).to_dict()
        assert d["scan_types"] == []


class TestTargetRoundTrip:
    def test_round_trip(self):
        original = _make_target()
        assert Target.from_dict(original.to_dict()) == original

    def test_from_dict_defaults_optional_fields(self):
        data = {
            "target_id": "t1",
            "target_type": "web2",
            "target_url": "https://example.com",
            "registered_at": "2026-01-01T00:00:00Z",
        }
        target = Target.from_dict(data)
        assert target.scan_types == []
        assert target.notes == ""

    @pytest.mark.parametrize("target_type", list(TargetType))
    def test_all_target_types_survive_round_trip(self, target_type):
        original = _make_target(target_type=target_type.value)
        assert Target.from_dict(original.to_dict()) == original
