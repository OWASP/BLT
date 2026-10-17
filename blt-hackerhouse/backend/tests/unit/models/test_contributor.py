"""Unit tests for the Contributor model."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from models.contributor import Contributor, ContributorSnapshot


class TestContributorConstruction:
    def test_minimal_contributor(self):
        c = Contributor(display_name="Rudra Pratap Singh")
        assert c.display_name == "Rudra Pratap Singh"
        assert c.usernames == []
        assert c.aliases == []
        assert c.platform_ids == {}
        assert c.is_linked is False
        assert c.score == 0

    def test_full_contributor(self):
        c = Contributor(
            display_name="Rudra Pratap Singh",
            usernames=["rudra-rps", "rudra_pratap_singh"],
            aliases=["Rudra Singh"],
            platform_ids={"gitlab_id": "12345", "blt_id": "678"},
            is_linked=True,
            score=142,
        )
        assert len(c.usernames) == 2
        assert c.platform_ids["gitlab_id"] == "12345"
        assert c.is_linked is True
        assert c.score == 142

    def test_empty_display_name_rejected(self):
        with pytest.raises(ValidationError, match="display_name"):
            Contributor(display_name="")

    def test_negative_score_rejected_by_model(self):
        c = Contributor(display_name="test", score=0)
        with pytest.raises(ValueError, match="non-negative"):
            c.add_score(-5)


class TestUsernameManagement:
    def test_add_username_appends_lowercase(self):
        c = Contributor(display_name="Test")
        c.add_username("Rudra-RPS")
        assert c.usernames == ["rudra-rps"]

    def test_add_username_deduplicates(self):
        c = Contributor(display_name="Test")
        c.add_username("rudra-rps")
        c.add_username("rudra-rps")
        c.add_username("RUDRA-RPS")
        assert len(c.usernames) == 1

    def test_add_blank_username_ignored(self):
        c = Contributor(display_name="Test")
        c.add_username("  ")
        assert c.usernames == []


class TestAliasManagement:
    def test_add_alias_appends(self):
        c = Contributor(display_name="Test")
        c.add_alias("Rudra Pratap Singh")
        assert c.aliases == ["Rudra Pratap Singh"]

    def test_add_alias_deduplicates(self):
        c = Contributor(display_name="Test")
        c.add_alias("Rudra Singh")
        c.add_alias("Rudra Singh")
        assert len(c.aliases) == 1

    def test_add_blank_alias_ignored(self):
        c = Contributor(display_name="Test")
        c.add_alias("")
        assert c.aliases == []


class TestPlatformIdManagement:
    def test_add_platform_id_sets_is_linked_on_second_platform(self):
        c = Contributor(display_name="Test")
        c.add_platform_id("gitlab", "12345")
        assert c.is_linked is False
        c.add_platform_id("blt", "678")
        assert c.is_linked is True

    def test_add_same_platform_id_overwrites(self):
        c = Contributor(display_name="Test")
        c.add_platform_id("gitlab", "12345")
        c.add_platform_id("gitlab", "99999")
        assert c.platform_ids["gitlab_id"] == "99999"


class TestScoreManagement:
    def test_add_score_increments(self):
        c = Contributor(display_name="Test")
        c.add_score(10)
        c.add_score(5)
        assert c.score == 15

    def test_add_score_zero_is_noop(self):
        c = Contributor(display_name="Test", score=42)
        c.add_score(0)
        assert c.score == 42


class TestContributorSnapshot:
    def test_from_contributor_with_avatar_state(self):
        c = Contributor(
            display_name="Rudra Pratap Singh",
            is_linked=True,
            score=42,
        )
        snap = ContributorSnapshot.from_contributor(
            c, floor=2, room="merge_request_room", last_event="mr_opened",
        )
        assert snap.id == c.id
        assert snap.display_name == "Rudra Pratap Singh"
        assert snap.floor == 2
        assert snap.room == "merge_request_room"
        assert snap.identity_linked is True
        assert snap.last_event == "mr_opened"
        assert snap.score == 42

    def test_from_contributor_without_avatar_state(self):
        c = Contributor(display_name="New User")
        snap = ContributorSnapshot.from_contributor(c)
        assert snap.floor is None
        assert snap.room is None
        assert snap.last_event is None
        assert snap.score == 0

    def test_floor_bounds_validation(self):
        with pytest.raises(ValidationError):
            ContributorSnapshot(
                id=uuid4(), display_name="test", floor=0,
            )
        with pytest.raises(ValidationError):
            ContributorSnapshot(
                id=uuid4(), display_name="test", floor=4,
            )
