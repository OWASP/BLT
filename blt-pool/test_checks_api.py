"""Unit tests for src/checks_api.py."""

import pathlib
import sys
import warnings

import pytest

_SRC_PATH = pathlib.Path(__file__).parent / "src"
sys.path.insert(0, str(_SRC_PATH))

from checks_api import (  # noqa: E402
    MAX_ANNOTATIONS_PER_REQUEST,
    batch_annotations,
    build_create_check_run_payload,
    build_update_check_run_payloads,
    normalize_conclusion,
)


def test_normalize_conclusion_aliases_and_default():
    assert normalize_conclusion("pass") == "success"
    assert normalize_conclusion("warning") == "neutral"
    assert normalize_conclusion("timeout") == "timed_out"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert normalize_conclusion("unknown-value") == "neutral"
        assert len(caught) == 1
    assert normalize_conclusion(None) == "neutral"


def test_normalize_conclusion_valid_passthrough_and_custom_default():
    assert normalize_conclusion("success") == "success"
    assert normalize_conclusion("", default="failure") == "failure"


def test_batch_annotations_chunks_by_limit():
    annotations = [{"path": "src/a.py", "start_line": i, "end_line": i} for i in range(1, 121)]
    batches = batch_annotations(annotations)
    assert len(batches) == 3
    assert len(batches[0]) == MAX_ANNOTATIONS_PER_REQUEST
    assert len(batches[1]) == MAX_ANNOTATIONS_PER_REQUEST
    assert len(batches[2]) == 20


def test_batch_annotations_invalid_size_raises():
    with pytest.raises(ValueError):
        batch_annotations([{"path": "src/a.py"}], batch_size=0)
    with pytest.raises(ValueError):
        batch_annotations([{"path": "src/a.py"}], batch_size=-1)
    with pytest.raises(ValueError):
        batch_annotations([], batch_size=0)


def test_build_create_check_run_payload_defaults():
    payload = build_create_check_run_payload(name="Security Scan", head_sha="abc123")
    assert payload["name"] == "Security Scan"
    assert payload["head_sha"] == "abc123"
    assert payload["status"] == "in_progress"
    assert payload["started_at"].endswith("Z")


def test_build_create_check_run_payload_optional_fields_and_status():
    payload = build_create_check_run_payload(
        name="Security Scan",
        head_sha="abc123",
        status="queued",
        details_url="https://example.com/details",
        external_id="scan-1",
    )
    assert payload["status"] == "queued"
    assert payload["details_url"] == "https://example.com/details"
    assert payload["external_id"] == "scan-1"


def test_build_create_check_run_payload_invalid_status_raises():
    with pytest.raises(ValueError):
        build_create_check_run_payload(name="Security Scan", head_sha="abc123", status="done")


def test_build_create_check_run_payload_completed_status_rejected():
    with pytest.raises(ValueError, match="build_create_check_run_payload"):
        build_create_check_run_payload(name="Security Scan", head_sha="abc123", status="completed")


def test_build_update_check_run_payloads_completed_with_pagination():
    annotations = [
        {
            "path": "src/a.py",
            "start_line": i,
            "end_line": i,
            "annotation_level": "warning",
            "message": "m",
        }
        for i in range(1, 53)
    ]

    payloads = build_update_check_run_payloads(
        status="completed",
        conclusion="failed",
        title="Security Results",
        summary="findings",
        annotations=annotations,
    )

    assert len(payloads) == 2
    assert "check_run_id" not in payloads[0]
    assert payloads[0]["status"] == "completed"
    assert payloads[0]["conclusion"] == "failure"
    assert len(payloads[0]["output"]["annotations"]) == 50
    assert len(payloads[1]["output"]["annotations"]) == 2
    assert payloads[0]["output"]["title"].endswith("(1/2)")
    assert payloads[1]["output"]["title"].endswith("(2/2)")


def test_build_update_check_run_payloads_invalid_status_raises():
    with pytest.raises(ValueError):
        build_update_check_run_payloads(
            status="done",
            title="t",
            summary="s",
        )


def test_build_update_check_run_payloads_in_progress_with_text():
    payloads = build_update_check_run_payloads(
        status="in_progress",
        title="Scan Running",
        summary="still processing",
        text="step 2/4",
        annotations=[{"path": "src/a.py", "start_line": 1, "end_line": 1}],
    )
    assert len(payloads) == 1
    assert payloads[0]["status"] == "in_progress"
    assert "conclusion" not in payloads[0]
    assert payloads[0]["output"]["text"] == "step 2/4"


def test_build_update_check_run_payloads_completed_requires_conclusion():
    with pytest.raises(ValueError):
        build_update_check_run_payloads(
            status="completed",
            title="Done",
            summary="finished",
        )


def test_build_update_check_run_payloads_none_and_empty_annotations_match():
    payload_none = build_update_check_run_payloads(
        status="in_progress",
        title="No Ann",
        summary="none",
        annotations=None,
    )
    payload_empty = build_update_check_run_payloads(
        status="in_progress",
        title="No Ann",
        summary="none",
        annotations=[],
    )
    assert payload_none == payload_empty
    assert payload_none[0]["output"]["annotations"] == []


def test_build_update_check_run_payloads_explicit_completed_at():
    payloads = build_update_check_run_payloads(
        status="completed",
        title="Done",
        summary="finished",
        conclusion="success",
        completed_at="2026-03-14T00:00:00Z",
    )
    assert payloads[0]["completed_at"] == "2026-03-14T00:00:00Z"
