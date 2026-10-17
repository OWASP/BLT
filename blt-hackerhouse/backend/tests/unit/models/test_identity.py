"""Unit tests for IdentityMapping and IdentityFlag models."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from models.identity import IdentityMapping, IdentityFlag, PlatformIdentity


class TestIdentityMapping:
    def test_minimal_mapping(self):
        cid = uuid4()
        m = IdentityMapping(
            platform="gitlab",
            platform_user_id="12345",
            contributor_id=cid,
            confidence=1.0,
        )
        assert m.platform == "gitlab"
        assert m.platform_user_id == "12345"
        assert m.contributor_id == cid
        assert m.confidence == 1.0
        assert m.id is None  # not yet persisted
        assert m.confirmed_by is None

    def test_mapping_with_confirmation(self):
        m = IdentityMapping(
            platform="blt",
            platform_user_id="678",
            contributor_id=uuid4(),
            confidence=0.75,
            confirmed_by="maintainer-donnie",
        )
        assert m.confirmed_by == "maintainer-donnie"

    def test_invalid_platform_rejected(self):
        with pytest.raises(ValidationError, match="platform"):
            IdentityMapping(
                platform="github",  # no longer valid
                platform_user_id="1",
                contributor_id=uuid4(),
                confidence=1.0,
            )

    def test_confidence_bounds(self):
        cid = uuid4()
        # 0.0 is valid
        m = IdentityMapping(platform="gitlab", platform_user_id="1", contributor_id=cid, confidence=0.0)
        assert m.confidence == 0.0

        # 1.0 is valid
        m = IdentityMapping(platform="gitlab", platform_user_id="1", contributor_id=cid, confidence=1.0)
        assert m.confidence == 1.0

        # Negative
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            IdentityMapping(platform="gitlab", platform_user_id="1", contributor_id=cid, confidence=-0.1)

        # Above 1.0
        with pytest.raises(ValidationError, match="less than or equal to 1"):
            IdentityMapping(platform="gitlab", platform_user_id="1", contributor_id=cid, confidence=1.1)

    def test_empty_platform_user_id_rejected(self):
        with pytest.raises(ValidationError, match="platform_user_id"):
            IdentityMapping(
                platform="gitlab",
                platform_user_id="",
                contributor_id=uuid4(),
                confidence=1.0,
            )


class TestPlatformIdentity:
    def test_gitlab_identity(self):
        pi = PlatformIdentity(platform="gitlab", username="rudra-rps", user_id="12345")
        assert pi.platform == "gitlab"
        assert pi.username == "rudra-rps"

    def test_blt_identity(self):
        pi = PlatformIdentity(platform="blt", user_id="678")
        assert pi.platform == "blt"
        assert pi.username is None

    def test_invalid_platform(self):
        with pytest.raises(ValidationError, match="platform"):
            PlatformIdentity(platform="discord", user_id="x")


class TestIdentityFlag:
    def test_identity_flag_construction(self):
        flag = IdentityFlag(
            source_a=PlatformIdentity(platform="gitlab", username="rudra-rps", user_id="12345"),
            source_b=PlatformIdentity(platform="blt", user_id="678"),
            confidence=0.75,
            contributor_id=uuid4(),
        )
        assert flag.confidence == 0.75
        assert flag.source_a.platform == "gitlab"
        assert flag.source_b.platform == "blt"

    def test_identity_flag_confidence_bounds(self):
        base = {
            "source_a": PlatformIdentity(platform="gitlab", username="x", user_id="1"),
            "source_b": PlatformIdentity(platform="blt", user_id="2"),
            "contributor_id": uuid4(),
        }
        # valid
        IdentityFlag(**base, confidence=0.0)
        IdentityFlag(**base, confidence=1.0)
        # invalid
        with pytest.raises(ValidationError):
            IdentityFlag(**base, confidence=-0.1)
        with pytest.raises(ValidationError):
            IdentityFlag(**base, confidence=1.1)
