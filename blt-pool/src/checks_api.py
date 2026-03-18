"""Helpers for constructing GitHub Checks API payloads.

This module is intentionally framework-agnostic so callers can use it with any
HTTP client. It focuses on:
1) conclusion normalization,
2) annotation batching (GitHub max 50 per request),
3) request payload generation for create/update check-run calls.
"""

from __future__ import annotations

from datetime import datetime, timezone
import warnings

MAX_ANNOTATIONS_PER_REQUEST = 50

_VALID_STATUSES = {"queued", "in_progress", "completed"}
_VALID_CONCLUSIONS = {
    "action_required",
    "cancelled",
    "failure",
    "neutral",
    "success",
    "skipped",
    "stale",
    "timed_out",
}
_CONCLUSION_ALIASES = {
    "ok": "success",
    "pass": "success",
    "passed": "success",
    "error": "failure",
    "failed": "failure",
    "warn": "neutral",
    "warning": "neutral",
    "info": "neutral",
    "canceled": "cancelled",
    "timeout": "timed_out",
    "manual": "action_required",
}


def _utc_now_iso() -> str:
    """Return an RFC3339 UTC timestamp (GitHub-compatible)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_conclusion(value: str | None, default: str = "neutral") -> str:
    """Normalize free-form conclusion values to GitHub-supported conclusions."""
    if not value:
        return default

    normalized = value.strip().lower().replace(" ", "_")
    normalized = _CONCLUSION_ALIASES.get(normalized, normalized)
    if normalized in _VALID_CONCLUSIONS:
        return normalized
    warnings.warn(
        f"Unknown conclusion {value!r}, defaulting to {default!r}",
        UserWarning,
        stacklevel=2,
    )
    return default


def batch_annotations(
    annotations: list[dict] | None,
    batch_size: int = MAX_ANNOTATIONS_PER_REQUEST,
) -> list[list[dict]]:
    """Split annotation payloads into GitHub-compatible chunks."""
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")
    if not annotations:
        return []

    return [annotations[i : i + batch_size] for i in range(0, len(annotations), batch_size)]


def build_create_check_run_payload(
    *,
    name: str,
    head_sha: str,
    status: str = "in_progress",
    details_url: str | None = None,
    external_id: str | None = None,
    started_at: str | None = None,
) -> dict:
    """Construct payload for POST /repos/{owner}/{repo}/check-runs."""
    if status not in _VALID_STATUSES:
        raise ValueError(f"invalid status: {status}")
    if status == "completed":
        raise ValueError(
            "build_create_check_run_payload does not support status='completed'; "
            "use build_update_check_run_payloads to set conclusion and complete the run"
        )

    payload = {
        "name": name,
        "head_sha": head_sha,
        "status": status,
        "started_at": started_at or _utc_now_iso(),
    }
    if details_url:
        payload["details_url"] = details_url
    if external_id:
        payload["external_id"] = external_id
    return payload


def build_update_check_run_payloads(
    *,
    status: str,
    title: str,
    summary: str,
    conclusion: str | None = None,
    text: str | None = None,
    annotations: list[dict] | None = None,
    completed_at: str | None = None,
) -> list[dict]:
    """Build one or more PATCH payloads for check-run updates.

    If annotations exceed GitHub's limit, multiple payloads are produced with
    output annotations split into 50-item chunks.
    """
    if status not in _VALID_STATUSES:
        raise ValueError(f"invalid status: {status}")

    normalized_conclusion = None
    if status == "completed":
        if conclusion is None:
            raise ValueError("conclusion is required when status is 'completed'")
        normalized_conclusion = normalize_conclusion(conclusion)

    annotation_batches = batch_annotations(annotations)
    if not annotation_batches:
        annotation_batches = [[]]

    payloads: list[dict] = []
    for index, chunk in enumerate(annotation_batches):
        payload = {
            "status": status,
            "output": {
                "title": title,
                "summary": summary,
                "annotations": chunk,
            },
        }
        if text:
            payload["output"]["text"] = text
        if status == "completed":
            payload["conclusion"] = normalized_conclusion
            payload["completed_at"] = completed_at or _utc_now_iso()

        # Keep title unique across pages to make annotation pagination obvious.
        if len(annotation_batches) > 1:
            payload["output"]["title"] = f"{title} ({index + 1}/{len(annotation_batches)})"

        payloads.append(payload)

    return payloads
