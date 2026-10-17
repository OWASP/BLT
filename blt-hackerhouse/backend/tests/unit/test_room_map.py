"""Room routing map tests."""

from __future__ import annotations

from src.state.room_map import DEFAULT_ROOM, ROOM_MAP, resolve_room


def test_known_event_types_route_correctly():
    assert resolve_room("mr_merged").room == "release_management_room"
    assert resolve_room("mr_opened").floor == 2
    assert resolve_room("review_requested").floor == 3
    assert resolve_room("bug_bounty_submitted").floor == 1


def test_unknown_routes_to_default():
    entry = resolve_room("unknown")
    assert entry == DEFAULT_ROOM
    assert entry.room == "activity_monitor"


def test_no_mentorship_rooms_present():
    # From MIGRATION_IMPACT.md: mentor office + strategy war room removed.
    all_rooms = {entry.room for entry in ROOM_MAP.values()}
    assert "mentor_office" not in all_rooms
    assert "strategy_war_room" not in all_rooms