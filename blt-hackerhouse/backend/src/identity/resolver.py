"""Four-stage identity resolution pipeline (VF07).

Stage 1 — Exact platform match (lookup in ``identity_mappings``)
Stage 2 — Levenshtein ≤ 2 against known usernames (confidence 0.75)
Stage 3 — Jaccard (token_set_ratio) ≥ 0.6 against aliases (confidence 0.60)
Stage 4 — Unlinked fallback: insert a new contributor + mapping
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID, uuid4

import aiosqlite
from rapidfuzz import distance, fuzz

from ..models.contributor import Contributor
from ..models.event import Event
from ..models.identity import IdentityFlag, IdentityMapping, PlatformIdentity
from ..storage import (
    AvatarStateQueries,
    ContributorQueries,
    Database,
    IdentityQueries,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolutionResult:
    """Outcome of resolving a single event's actor."""

    contributor_id: UUID
    confidence: float
    is_new: bool
    flag: IdentityFlag | None = None


class IdentityResolver:
    """Resolve an event's actor to a unified ``Contributor``."""

    def __init__(self, db: Database) -> None:
        self.db = db
        self.contributors = ContributorQueries(db)
        self.identities = IdentityQueries(db)
        self.avatars = AvatarStateQueries(db)

    async def resolve(self, event: Event, conn: aiosqlite.Connection | None = None) -> ResolutionResult:
        """Run all four stages and return the resolved contributor."""
        platform = event.source
        platform_user_id = event.actor_id
        actor_name = event.actor_name.strip()

        # Stage 1: exact platform match
        existing_mapping = await self.identities.lookup(platform, platform_user_id)
        if existing_mapping is not None:
            logger.debug(
                "identity stage1 exact",
                extra={"platform": platform, "user_id": platform_user_id},
            )
            return ResolutionResult(
                contributor_id=existing_mapping.contributor_id,
                confidence=existing_mapping.confidence,
                is_new=False,
            )

        contributors = await self.contributors.list_all()
        actor_lower = actor_name.lower()

        # Stage 2: Levenshtein ≤ 2 against known usernames
        for contributor in contributors:
            for username in contributor.usernames:
                if not username:
                    continue
                if distance.Levenshtein.distance(actor_lower, username) <= 2:
                    flag = await self._record_fuzzy_match(
                        contributor, platform, platform_user_id, actor_name, 0.75, conn
                    )
                    return ResolutionResult(
                        contributor_id=contributor.id,
                        confidence=0.75,
                        is_new=False,
                        flag=flag,
                    )

        # Stage 3: token_set_ratio ≥ 0.6 against aliases
        for contributor in contributors:
            for alias in contributor.aliases + [contributor.display_name]:
                score = fuzz.token_set_ratio(actor_lower, alias.lower()) / 100.0
                if score >= 0.60:
                    flag = await self._record_fuzzy_match(
                        contributor, platform, platform_user_id, actor_name, 0.60, conn
                    )
                    return ResolutionResult(
                        contributor_id=contributor.id,
                        confidence=0.60,
                        is_new=False,
                        flag=flag,
                    )

        # Stage 4: unlinked fallback
        return await self._create_unlinked(platform, platform_user_id, actor_name, conn)

    async def _record_fuzzy_match(
        self,
        contributor: Contributor,
        platform: str,
        platform_user_id: str,
        actor_name: str,
        confidence: float,
        conn: aiosqlite.Connection | None = None,
    ) -> IdentityFlag:
        """Insert the new mapping and emit an identity flag."""
        await self.identities.insert(
            IdentityMapping(
                platform=platform,  # type: ignore[arg-type]
                platform_user_id=platform_user_id,
                contributor_id=contributor.id,
                confidence=confidence,
            ),
            conn=conn,
        )
        contributor.add_username(actor_name)
        contributor.add_platform_id(platform, platform_user_id)
        await self.contributors.upsert(contributor, conn=conn)

        flag = IdentityFlag(
            source_a=PlatformIdentity(platform=platform, user_id=platform_user_id),  # type: ignore[arg-type]
            source_b=PlatformIdentity(
                platform="blt" if platform == "gitlab" else "gitlab",  # type: ignore[arg-type]
                username=contributor.display_name,
            ),
            confidence=confidence,
            contributor_id=contributor.id,
        )
        logger.info(
            "identity fuzzy match",
            extra={
                "contributor_id": str(contributor.id),
                "platform": platform,
                "confidence": confidence,
            },
        )
        return flag

    async def _create_unlinked(
        self,
        platform: str,
        platform_user_id: str,
        actor_name: str,
        conn: aiosqlite.Connection | None = None,
    ) -> ResolutionResult:
        contributor = Contributor(
            id=uuid4(),
            display_name=actor_name,
            usernames=[actor_name.lower()],
            aliases=[actor_name],
            platform_ids={f"{platform}_id": platform_user_id},
            is_linked=False,
            score=0,
        )
        await self.contributors.upsert(contributor, conn=conn)
        await self.identities.insert(
            IdentityMapping(
                platform=platform,  # type: ignore[arg-type]
                platform_user_id=platform_user_id,
                contributor_id=contributor.id,
                confidence=0.0,
            ),
            conn=conn,
        )
        logger.info(
            "identity unlinked fallback",
            extra={
                "contributor_id": str(contributor.id),
                "platform": platform,
                "actor_name": actor_name,
            },
        )
        return ResolutionResult(
            contributor_id=contributor.id,
            confidence=0.0,
            is_new=True,
        )