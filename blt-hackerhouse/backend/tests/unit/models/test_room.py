"""Unit tests for Room models."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from models.room import AvatarState, RoomMapEntry, RoomOccupancy


class TestRoomMapEntry:
    def test_valid_entry(self):
        entry = RoomMapEntry(floor=2, room="merge_request_room")
        assert entry.floor == 2
        assert entry.room == "merge_request_room"

    def test_floor_below_1_rejected(self):
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            RoomMapEntry(floor=0, room="room")

    def test_floor_above_3_rejected(self):
        with pytest.raises(ValidationError, match="less than or equal to 3"):
            RoomMapEntry(floor=4, room="room")

    def test_empty_room_rejected(self):
        with pytest.raises(ValidationError, match="room"):
            RoomMapEntry(floor=1, room="")


class TestAvatarState:
    def test_valid_state(self):
        cid = uuid4()
        state = AvatarState(
            contributor_id=cid,
            floor=2,
            room="merge_request_room",
            last_event="mr_opened",
        )
        assert state.contributor_id == cid
        assert state.floor == 2
        assert state.room == "merge_request_room"
        assert state.last_event == "mr_opened"

    def test_floor_bounds(self):
        cid = uuid4()
        # Floor 1 valid
        s = AvatarState(contributor_id=cid, floor=1, room="a", last_event="x")
        assert s.floor == 1
        # Floor 3 valid
        s = AvatarState(contributor_id=cid, floor=3, room="a", last_event="x")
        assert s.floor == 3
        # Floor 0 invalid
        with pytest.raises(ValidationError):
            AvatarState(contributor_id=cid, floor=0, room="a", last_event="x")
        # Floor 4 invalid
        with pytest.raises(ValidationError):
            AvatarState(contributor_id=cid, floor=4, room="a", last_event="x")

    def test_empty_last_event_rejected(self):
        with pytest.raises(ValidationError, match="last_event"):
            AvatarState(
                contributor_id=uuid4(),
                floor=1,
                room="a",
                last_event="",
            )

    def test_empty_room_rejected(self):
        with pytest.raises(ValidationError, match="room"):
            AvatarState(
                contributor_id=uuid4(),
                floor=1,
                room="",
                last_event="x",
            )


class TestRoomOccupancy:
    def test_empty_occupancy(self):
        occ = RoomOccupancy()
        assert occ.occupancy == {}

    def test_from_avatar_states(self):
        cid1, cid2, cid3 = uuid4(), uuid4(), uuid4()
        states = [
            AvatarState(contributor_id=cid1, floor=1, room="issue_triage_desk", last_event="issue_opened"),
            AvatarState(contributor_id=cid2, floor=1, room="issue_triage_desk", last_event="issue_opened"),
            AvatarState(contributor_id=cid3, floor=2, room="merge_request_room", last_event="mr_opened"),
        ]
        occ = RoomOccupancy.from_avatar_states(states)
        assert occ.occupancy == {
            "issue_triage_desk": 2,
            "merge_request_room": 1,
        }

    def test_from_empty_list(self):
        occ = RoomOccupancy.from_avatar_states([])
        assert occ.occupancy == {}

    def test_single_contributor(self):
        cid = uuid4()
        state = AvatarState(
            contributor_id=cid, floor=3, room="code_review_room", last_event="review_requested",
        )
        occ = RoomOccupancy.from_avatar_states([state])
        assert occ.occupancy == {"code_review_room": 1}
