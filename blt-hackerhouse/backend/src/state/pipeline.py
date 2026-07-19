"""Pipeline runner (VF10).

Consumes events from the queue, persists them, resolves identity,
updates avatar state, computes room occupancy, scores the
leaderboard, and broadcasts the resulting messages.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from ..broadcast.hub import WebSocketHub
from ..broadcast.leaderboard import LeaderboardAccumulator
from ..broadcast.messages import (
    build_avatar_move,
    build_identity_flag,
    build_leaderboard_update,
    build_snapshot,
)
from ..core.dedup import is_duplicate, record_if_absent
from ..models.contributor import Contributor
from ..models.event import Event
from ..models.room import AvatarState
from ..state.queue import EventQueue
from ..state.room_map import resolve_room
from ..storage import (
    AvatarStateQueries,
    ContributorQueries,
    Database,
    DeadLetterQueries,
    EventQueries,
    IdentityQueries,
)


logger = logging.getLogger(__name__)


class _PipelineSkip(Exception):
    """Raised to skip broadcast and commit when an event is a duplicate or missing contributor."""


class PipelineRunner:
    """Drains the EventQueue, applying the full downstream pipeline."""

    def __init__(
        self,
        *,
        db: Database,
        queue: EventQueue,
        hub: WebSocketHub,
        leaderboard: LeaderboardAccumulator | None = None,
        poll_interval: float = 0.05,
    ) -> None:
        self.db = db
        self.queue = queue
        self.hub = hub
        self.leaderboard = leaderboard or LeaderboardAccumulator()
        self._poll_interval = poll_interval
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._sequence = 0
        self._lock = asyncio.Lock()

        self.events_q = EventQueries(db)
        self.contributors_q = ContributorQueries(db)
        self.avatars_q = AvatarStateQueries(db)
        self.identity_q = IdentityQueries(db)
        self.dlq = DeadLetterQueries(db)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self._sequence = await self.events_q.max_sequence_number()
        logger.info("pipeline sequence seeded", extra={"seq": self._sequence})
        self._task = asyncio.create_task(self._run(), name="pipeline-runner")
        logger.info("pipeline runner started")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        try:
            await asyncio.wait_for(self._task, timeout=5.0)
        except asyncio.TimeoutError:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("pipeline runner stopped")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def _run(self) -> None:
        from ..identity.resolver import IdentityResolver

        resolver = IdentityResolver(self.db)
        while not self._stop_event.is_set():
            try:
                event = await asyncio.wait_for(self.queue.get(), timeout=self._poll_interval * 10)
            except asyncio.TimeoutError:
                continue
            try:
                await self._process_event(event, resolver)
            except _PipelineSkip:
                pass
            except Exception as exc:  # noqa: BLE001
                logger.exception("pipeline event failed")
                self.hub.record_error()
                try:
                    await self.dlq.add(
                        event_id=str(event.id),
                        source=event.source,
                        error=repr(exc),
                        payload=event.model_dump(mode="json"),
                    )
                except Exception:  # noqa: BLE001
                    logger.exception("dlq add failed")
            finally:
                self.queue.task_done()

    async def _process_event(self, event: Event, resolver) -> None:
        async with self.db.transaction() as conn:
            # 1. Dedup + persist
            inserted = await record_if_absent(self.db, event, conn=conn)
            if not inserted:
                logger.info("pipeline dedup dropped", extra={
                    "key": event.idempotency_key, "source": event.source, "type": event.event_type,
                })
                raise _PipelineSkip()

            async with self._lock:
                self._sequence += 1
                await self.events_q.assign_sequence(event.id, self._sequence, conn=conn)

            # 2. Identity resolution
            result = await resolver.resolve(event, conn=conn)
            contributor = await self.contributors_q.get(result.contributor_id, conn=conn)
            if contributor is None:
                logger.warning("pipeline missing contributor", extra={"id": str(result.contributor_id)})
                raise _PipelineSkip()

            # 3. Update avatar state
            room = resolve_room(event.event_type)
            avatar = AvatarState(
                contributor_id=contributor.id,
                floor=room.floor,
                room=room.room,
                last_event=event.event_type,
                updated_at=datetime.now(tz=timezone.utc).replace(microsecond=0),
            )
            await self.avatars_q.upsert(avatar, conn=conn)

            # 4. Score leaderboard
            delta = self.leaderboard.record(str(contributor.id), event.event_type, event.metadata)
            if delta:
                contributor.add_score(delta)
                await self.contributors_q.upsert(contributor, conn=conn)

        # 5. Broadcast (outside transaction)
        self.hub.record_event()
        await self.hub.broadcast(
            build_avatar_move(event, floor=room.floor, room=room.room, contributor_id=contributor.id)
        )
        if result.flag is not None:
            try:
                await self.hub.broadcast(build_identity_flag(result.flag))
            except Exception:  # noqa: BLE001
                logger.exception("identity_flag broadcast failed")
        if delta:
            await self.hub.broadcast(
                build_leaderboard_update(
                    contributor_id=contributor.id,
                    score=contributor.score,
                    delta=delta,
                    last_event=event.event_type,
                )
            )

    # ------------------------------------------------------------------
    # Snapshot helpers
    # ------------------------------------------------------------------

    async def build_snapshot(self):
        contributors = await self.contributors_q.list_all()
        avatars_list = await self.avatars_q.list_all()
        avatar_map: dict[UUID, AvatarState] = {a.contributor_id: a for a in avatars_list}
        occupancy = await self.avatars_q.occupancy()
        return build_snapshot(contributors, avatar_map, occupancy)

    async def room_occupancy(self) -> dict[str, int]:
        return await self.avatars_q.occupancy()

    async def events_last_minute(self) -> int:
        since = datetime.now(tz=timezone.utc).replace(microsecond=0) - timedelta(minutes=1)
        return await self.events_q.count_since(since)