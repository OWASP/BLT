"""Room routing map (VF08).

Maps each internal ``event_type`` to a (floor, room) tuple. Any
unmapped event type (including ``"unknown"``) routes to the default
Activity Monitor room on Floor 1.
"""

from __future__ import annotations

from typing import Final

from ..models.room import RoomMapEntry


# Authoritative routing per MVP_V1_SPEC.md §VF08.
ROOM_MAP: Final[dict[str, RoomMapEntry]] = {
    # Floor 1: Operations and Infrastructure
    "issue_opened":         RoomMapEntry(floor=1, room="issue_triage_desk"),
    "bug_bounty_submitted": RoomMapEntry(floor=1, room="bug_bounty_terminal"),
    "pipeline_run":         RoomMapEntry(floor=1, room="cicd_server_room"),
    "deploy_event":         RoomMapEntry(floor=1, room="deployment_control_center"),

    # Floor 2: Development Workspace
    "mr_opened":            RoomMapEntry(floor=2, room="merge_request_room"),
    "note_added":           RoomMapEntry(floor=2, room="contributor_workstations"),

    # Floor 3: Review and Leadership
    "review_requested":     RoomMapEntry(floor=3, room="code_review_room"),
    "mr_merged":            RoomMapEntry(floor=3, room="release_management_room"),
    "bug_status_change":    RoomMapEntry(floor=3, room="security_audit_room"),
    "hunt_activity":        RoomMapEntry(floor=3, room="leaderboard_wall"),
}

DEFAULT_ROOM: Final[RoomMapEntry] = RoomMapEntry(floor=1, room="activity_monitor")


def resolve_room(event_type: str) -> RoomMapEntry:
    """Return the (floor, room) for ``event_type`` or the default."""
    return ROOM_MAP.get(event_type, DEFAULT_ROOM)


def all_rooms() -> list[RoomMapEntry]:
    """Return every room referenced by the routing map plus the default."""
    seen: dict[tuple[int, str], RoomMapEntry] = {}
    for entry in ROOM_MAP.values():
        seen[(entry.floor, entry.room)] = entry
    seen[(DEFAULT_ROOM.floor, DEFAULT_ROOM.room)] = DEFAULT_ROOM
    return list(seen.values())