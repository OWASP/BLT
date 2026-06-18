"""Seed the database with a handful of demo contributors and events.

Usage:
    python -m scripts.seed
"""

from __future__ import annotations

import asyncio
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


DEMO_CONTRIBUTORS = [
    ("rudra-rps", "Rudra Pratap Singh", True),
    ("donnieb", "Donnie Brown", True),
    ("alice", "Alice Example", False),
    ("bob", "Bob Example", False),
]


async def main() -> int:
    configure_logging()
    db: Database = get_database()
    await db.connect()
    await db.run_migrations()

    contributor_q = ContributorQueries(db)
    avatar_q = AvatarStateQueries(db)
    event_q = EventQueries(db)

    for username, display, linked in DEMO_CONTRIBUTORS:
        contributor = Contributor(
            id=uuid4(),
            display_name=display,
            usernames=[username],
            aliases=[display],
            platform_ids={"gitlab_id": username},
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
            actor_id=username,
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