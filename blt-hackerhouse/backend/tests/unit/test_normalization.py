"""Tests for GitLab + BLT normalizers."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.normalization.blt import normalize_blt_bug, normalize_blt_hunt
from src.normalization.gitlab import normalize_gitlab_payload


def test_gitlab_issue_opened():
    payload = {
        "object_kind": "issue",
        "object_attributes": {
            "action": "open",
            "title": "Test issue",
            "url": "https://gitlab.com/owasp/blt/-/issues/1",
            "state": "opened",
            "iid": 1,
            "created_at": "2026-06-17T10:00:00.000Z",
        },
        "user": {"id": 42, "username": "alice"},
        "project": {"path_with_namespace": "owasp/blt"},
    }
    event = normalize_gitlab_payload(payload)
    assert event.source == "gitlab"
    assert event.event_type == "issue_opened"
    assert event.actor_id == "42"
    assert event.actor_name == "alice"
    assert event.repository == "owasp/blt"
    assert event.metadata["title"] == "Test issue"


def test_gitlab_mr_merged():
    payload = {
        "object_kind": "merge_request",
        "object_attributes": {
            "action": "merge",
            "title": "Add webhook",
            "state": "merged",
            "source_branch": "feat/x",
            "target_branch": "main",
            "iid": 9,
        },
        "user": {"id": 7, "username": "bob"},
        "project": {"path_with_namespace": "owasp/blt"},
    }
    event = normalize_gitlab_payload(payload)
    assert event.event_type == "mr_merged"
    assert event.metadata["source_branch"] == "feat/x"


def test_gitlab_pipeline_success():
    payload = {
        "object_kind": "pipeline",
        "object_attributes": {
            "status": "success",
            "id": 555,
            "ref": "main",
            "sha": "abc123",
        },
        "user": {"id": 9, "username": "ci-bot"},
        "project": {"path_with_namespace": "owasp/blt"},
    }
    event = normalize_gitlab_payload(payload)
    assert event.event_type == "pipeline_run"
    assert event.metadata["status"] == "success"


def test_gitlab_unknown_object_kind():
    event = normalize_gitlab_payload({"object_kind": "deployment", "user": {"id": 1, "username": "ci"}, "project": {"path_with_namespace": "x/y"}})
    assert event.event_type == "unknown"


def test_gitlab_note_added():
    payload = {
        "object_kind": "note",
        "object_attributes": {
            "note": "Looks good!",
            "url": "https://gitlab.com/x",
            "noteable_type": "MergeRequest",
            "noteable_id": 9,
        },
        "user": {"id": 3, "username": "reviewer"},
        "project": {"path_with_namespace": "owasp/blt"},
    }
    event = normalize_gitlab_payload(payload)
    assert event.event_type == "note_added"
    assert event.metadata["noteable_type"] == "MergeRequest"


def test_blt_bug_submitted():
    record = {
        "id": 100,
        "user": 5,
        "username": "hunter1",
        "hunt": {"id": 2, "domain": "example.com", "repo": "owasp/blt"},
        "status": "new",
        "created": "2026-06-17T09:30:00Z",
        "description": "Found an XSS",
        "url": "https://owaspblt.org/bugs/100",
    }
    event = normalize_blt_bug(record)
    assert event.source == "blt"
    assert event.event_type == "bug_bounty_submitted"
    assert event.actor_id == "5"
    assert event.actor_name == "hunter1"
    assert event.repository == "owasp/blt"


def test_blt_bug_status_change_when_modified_differs():
    record = {
        "id": 101,
        "user": 6,
        "username": "hunter2",
        "created": "2026-06-16T00:00:00Z",
        "modified": "2026-06-17T00:00:00Z",
        "status": "triaged",
    }
    event = normalize_blt_bug(record)
    assert event.event_type == "bug_status_change"


def test_blt_hunt_activity():
    record = {
        "id": 12,
        "user": 8,
        "username": "lead",
        "name": "OWASP Hunt",
        "domain": "owasp.org",
        "status": "active",
        "created": "2026-06-17T08:00:00Z",
    }
    event = normalize_blt_hunt(record)
    assert event.event_type == "hunt_activity"
    assert event.repository == "owasp.org"