"""In-process asyncio queue for normalized events (VF10)."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Deque

from ..models.event import Event


@dataclass
class QueueStats:
    depth: int
    enqueued_total: int
    dequeued_total: int


class EventQueue:
    """Bounded in-process async queue of normalized ``Event`` objects.

    Uses ``asyncio.Queue`` for fairness and ``deque`` for cheap stats.
    The queue is bounded to apply backpressure on misbehaving upstream
    producers.
    """

    def __init__(self, max_size: int = 1024) -> None:
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=max_size)
        self._enqueued = 0
        self._dequeued = 0

    async def put(self, event: Event) -> None:
        await self._queue.put(event)
        self._enqueued += 1

    async def get(self) -> Event:
        event = await self._queue.get()
        self._dequeued += 1
        return event

    def task_done(self) -> None:
        self._queue.task_done()

    def join(self) -> asyncio.Future[None]:
        return self._queue.join()

    def qsize(self) -> int:
        return self._queue.qsize()

    def stats(self) -> QueueStats:
        return QueueStats(
            depth=self._queue.qsize(),
            enqueued_total=self._enqueued,
            dequeued_total=self._dequeued,
        )

    @property
    def empty(self) -> bool:
        return self._queue.empty()