"""GitLab webhook payload normalizer (VF05).

Maps GitLab ``object_kind`` -> internal ``event_type`` and extracts
the actor, repository, timestamp, and metadata fields per
``MVP_V1_SPEC.md`` §VF05.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..models.event import Event


def normalize_gitlab_payload(
    payload: dict[str, Any],
    *,
    received_at: datetime | None = None,
) -> Event:
    """Convert a GitLab webhook payload dict into a unified ``Event``.

    Returns ``event_type='unknown'`` for payloads that don't match any
    known mapping. Never raises — callers can route ``unknown`` to the
    Activity Monitor.
    """
    object_kind = payload.get("object_kind", "")
    obj_attrs = payload.get("object_attributes") or {}
    user = payload.get("user") or {}
    project = payload.get("project") or {}

    actor_id = str(user.get("id") or payload.get("user_id") or "unknown")
    actor_name = str(user.get("username") or user.get("name") or "unknown")
    repository = str(project.get("path_with_namespace") or project.get("name") or "")

    event_type, metadata = _map_object_kind(object_kind, obj_attrs, payload)

    timestamp = _extract_timestamp(obj_attrs, payload)
    if timestamp is None:
        timestamp = received_at or datetime.now(tz=timezone.utc).replace(microsecond=0)

    return Event(
        source="gitlab",
        event_type=event_type,
        actor_id=actor_id,
        actor_name=actor_name,
        repository=repository,
        timestamp=timestamp,
        metadata=metadata,
    )


def _map_object_kind(
    object_kind: str,
    obj_attrs: dict[str, Any],
    payload: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Apply the GitLab ``object_kind`` → internal ``event_type`` mapping."""

    if object_kind == "issue":
        action = obj_attrs.get("action")
        if action in ("open", "reopen"):
            return "issue_opened", _issue_metadata(obj_attrs)
        return "unknown", {"action": action, **(obj_attrs or {})}

    if object_kind == "merge_request":
        action = obj_attrs.get("action")
        if action == "open":
            return "mr_opened", _mr_metadata(obj_attrs)
        if action == "merge":
            return "mr_merged", _mr_metadata(obj_attrs)
        if action in ("approved", "review_requested", "requested_changes"):
            return "review_requested", _mr_metadata(obj_attrs)
        return "unknown", {"action": action, **(obj_attrs or {})}

    if object_kind == "pipeline":
        status = obj_attrs.get("status")
        if status in ("running", "success", "failed"):
            return "pipeline_run", _pipeline_metadata(obj_attrs)
        return "unknown", {"status": status, **(obj_attrs or {})}

    if object_kind == "note":
        return "note_added", _note_metadata(obj_attrs, payload)

    return "unknown", {"raw_object_kind": object_kind}


def _issue_metadata(obj_attrs: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": obj_attrs.get("title"),
        "description": obj_attrs.get("description"),
        "url": obj_attrs.get("url"),
        "state": obj_attrs.get("state"),
        "iid": obj_attrs.get("iid"),
        "action": obj_attrs.get("action"),
    }


def _mr_metadata(obj_attrs: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": obj_attrs.get("title"),
        "description": obj_attrs.get("description"),
        "url": obj_attrs.get("url"),
        "state": obj_attrs.get("state"),
        "iid": obj_attrs.get("iid"),
        "source_branch": obj_attrs.get("source_branch"),
        "target_branch": obj_attrs.get("target_branch"),
        "action": obj_attrs.get("action"),
    }


def _pipeline_metadata(obj_attrs: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": obj_attrs.get("status"),
        "pipeline_id": obj_attrs.get("id"),
        "ref": obj_attrs.get("ref"),
        "sha": obj_attrs.get("sha"),
        "url": obj_attrs.get("url"),
    }


def _note_metadata(obj_attrs: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    target_type = payload.get("noteable_type")
    return {
        "body": obj_attrs.get("note"),
        "url": obj_attrs.get("url"),
        "noteable_type": target_type,
        "noteable_id": payload.get("noteable_id"),
    }


def _extract_timestamp(obj_attrs: dict[str, Any], payload: dict[str, Any]) -> datetime | None:
    candidates = (
        obj_attrs.get("created_at"),
        obj_attrs.get("updated_at"),
        payload.get("created_at"),
    )
    for raw in candidates:
        if not raw:
            continue
        try:
            text = str(raw).replace("Z", "+00:00")
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed
        except (TypeError, ValueError):
            continue
    return None