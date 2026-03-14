"""Unit tests for src/checks_api.py."""

import pathlib
import sys

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
    assert normalize_conclusion("unknown-value") == "neutral"
    assert normalize_conclusion(None) == "neutral"


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


def test_build_create_check_run_payload_defaults():
    payload = build_create_check_run_payload(name="Security Scan", head_sha="abc123")
    assert payload["name"] == "Security Scan"
    assert payload["head_sha"] == "abc123"
    assert payload["status"] == "in_progress"
    assert payload["started_at"].endswith("Z")


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
        check_run_id=42,
        status="completed",
        conclusion="failed",
        title="Security Results",
        summary="findings",
        annotations=annotations,
    )

    assert len(payloads) == 2
    assert payloads[0]["check_run_id"] == 42
    assert payloads[0]["status"] == "completed"
    assert payloads[0]["conclusion"] == "failure"
    assert len(payloads[0]["output"]["annotations"]) == 50
    assert len(payloads[1]["output"]["annotations"]) == 2
    assert payloads[0]["output"]["title"].endswith("(1/2)")
    assert payloads[1]["output"]["title"].endswith("(2/2)")


def test_build_update_check_run_payloads_invalid_status_raises():
    with pytest.raises(ValueError):
        build_update_check_run_payloads(
            check_run_id=1,
            status="done",
            title="t",
            summary="s",
        )
