"""Unit tests for WebSocket message models."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from models.websocket import (
    SnapshotMessage,
    SnapshotData,
    SnapshotContributor,
    AvatarMoveMessage,
    IdentityFlagMessage,
    IdentityFlagLink,
    IdentityFlagSource,
    LeaderboardUpdateMessage,
)


class TestSnapshotMessage:
    def test_snapshot_message_construction(self):
        cid = uuid4()
        data = SnapshotData(
            contributors=[
                SnapshotContributor(
                    id=cid,
                    display_name="Test User",
                    floor=2,
                    room="merge_request_room",
                    identity_linked=True,
                    last_event="mr_opened",
                    score=42,
                )
            ],
            room_occupancy={"merge_request_room": 3, "code_review_room": 1},
        )
        msg = SnapshotMessage(data=data)
        assert msg.type == "snapshot"
        assert len(msg.data.contributors) == 1
        assert msg.data.contributors[0].display_name == "Test User"
        assert msg.data.room_occupancy["merge_request_room"] == 3

    def test_empty_snapshot(self):
        data = SnapshotData()
        msg = SnapshotMessage(data=data)
        assert msg.data.contributors == []
        assert msg.data.room_occupancy == {}
        assert msg.type == "snapshot"

    def test_generated_at_set_automatically(self):
        data = SnapshotData()
        msg = SnapshotMessage(data=data)
        assert msg.data.generated_at is not None


class TestAvatarMoveMessage:
    def test_valid_move(self):
        cid = uuid4()
        msg = AvatarMoveMessage(
            contributor_id=cid,
            floor=3,
            room="code_review_room",
            event_type="review_requested",
        )
        assert msg.type == "avatar_move"
        assert msg.contributor_id == cid
        assert msg.floor == 3
        assert msg.room == "code_review_room"
        assert msg.event_type == "review_requested"

    def test_negative_floor_rejected(self):
        with pytest.raises(ValidationError):
            AvatarMoveMessage(
                contributor_id=uuid4(),
                floor=0,
                room="a",
                event_type="x",
            )

    def test_floor_4_rejected(self):
        with pytest.raises(ValidationError):
            AvatarMoveMessage(
                contributor_id=uuid4(),
                floor=4,
                room="a",
                event_type="x",
            )

    def test_empty_room_rejected(self):
        with pytest.raises(ValidationError, match="room"):
            AvatarMoveMessage(
                contributor_id=uuid4(),
                floor=1,
                room="",
                event_type="x",
            )

    def test_empty_event_type_rejected(self):
        with pytest.raises(ValidationError, match="event_type"):
            AvatarMoveMessage(
                contributor_id=uuid4(),
                floor=1,
                room="a",
                event_type="",
            )


class TestIdentityFlagMessage:
    def test_valid_flag(self):
        msg = IdentityFlagMessage(
            suggested_link=IdentityFlagLink(
                source_a=IdentityFlagSource(platform="gitlab", username="rudra-rps"),
                source_b=IdentityFlagSource(platform="blt", user_id="678"),
                confidence=0.75,
            ),
            contributor_id=uuid4(),
        )
        assert msg.type == "identity_flag"
        assert msg.suggested_link.confidence == 0.75

    def test_confidence_bounds(self):
        link = IdentityFlagLink(
            source_a=IdentityFlagSource(platform="gitlab", username="x"),
            source_b=IdentityFlagSource(platform="blt", user_id="1"),
            confidence=0.60,
        )
        assert link.confidence == 0.60

        with pytest.raises(ValidationError):
            IdentityFlagLink(
                source_a=IdentityFlagSource(platform="gitlab", username="x"),
                source_b=IdentityFlagSource(platform="blt", user_id="1"),
                confidence=1.5,
            )


class TestLeaderboardUpdateMessage:
    def test_valid_update(self):
        cid = uuid4()
        msg = LeaderboardUpdateMessage(
            contributor_id=cid,
            score=47,
            delta=5,
            last_event="mr_merged",
        )
        assert msg.type == "leaderboard_update"
        assert msg.score == 47
        assert msg.delta == 5
        assert msg.last_event == "mr_merged"

    def test_negative_score_rejected(self):
        with pytest.raises(ValidationError):
            LeaderboardUpdateMessage(
                contributor_id=uuid4(),
                score=-1,
                delta=0,
                last_event="x",
            )

    def test_empty_last_event_rejected(self):
        with pytest.raises(ValidationError, match="last_event"):
            LeaderboardUpdateMessage(
                contributor_id=uuid4(),
                score=0,
                delta=0,
                last_event="",
            )
