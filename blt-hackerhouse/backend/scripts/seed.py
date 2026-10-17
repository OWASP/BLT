"""Seed the database with a handful of demo contributors and events.

Usage:
    APP_ENV=development python -m scripts.seed
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from src.core.logging import configure_logging, get_logger
from src.models.contributor import Contributor
from src.models.event import Event
from src.models.room import AvatarState
from src.state.room_map import resolve_room
from src.storage import (
    AvatarStateQueries,
    ContributorQueries,
    Database,
    EventQueries,
    get_database,
)


logger = get_logger(__name__)


# (gitlab_user_id, username, display_name, is_linked)
# GitLab platform IDs are numeric; the identity resolver matches on these.
DEMO_CONTRIBUTORS = [
    (10001, "rudra-rps", "Rudra Pratap Singh", True),
    (10002, "donnieb", "Donnie Brown", True),
    (10003, "alice", "Alice Example", False),
    (10004, "bob", "Bob Example", False),
]


def _require_safe_env() -> None:
    """Abort if not running in a non-production environment."""
    env = os.getenv("APP_ENV", "production")
    if env not in {"development", "test"}:
        raise SystemExit(
            f"seed.py must not run in {env!r}; set APP_ENV=development or APP_ENV=test"
        )


async def main() -> int:
    _require_safe_env()
    configure_logging()
    db: Database = get_database()
    await db.connect()
    await db.run_migrations()

    contributor_q = ContributorQueries(db)
    avatar_q = AvatarStateQueries(db)
    event_q = EventQueries(db)

    for gitlab_id, username, display, linked in DEMO_CONTRIBUTORS:
        contributor = Contributor(
            id=uuid4(),
            display_name=display,
            usernames=[username],
            aliases=[display],
            platform_ids={"gitlab_id": gitlab_id},
            is_linked=linked,
            score=0,
        )
        await contributor_q.upsert(contributor)

        now = datetime.now(tz=timezone.utc).replace(microsecond=0)
        room = resolve_room("mr_opened")
        await avatar_q.upsert(
            AvatarState(
                contributor_id=contributor.id,
                floor=room.floor,
                room=room.room,
                last_event="mr_opened",
                updated_at=now,
            )
        )
        event = Event(
            source="gitlab",
            event_type="mr_opened",
            actor_id=str(gitlab_id),
            actor_name=username,
            repository="OWASP-BLT/BLT",
            timestamp=now - timedelta(minutes=5),
            contributor_id=contributor.id,
        )
        await event_q.insert(event)
        contributor.add_score(2)
        await contributor_q.upsert(contributor)

    await db.close()
    logger.info("seed complete", extra={"contributors": len(DEMO_CONTRIBUTORS)})
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))