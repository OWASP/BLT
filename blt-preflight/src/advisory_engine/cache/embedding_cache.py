"""
embedding_cache.py

In-memory embedding cache for the BLT Preflight pipeline.

Responsibilities
----------------
- Cache embeddings by content hash
- Avoid recomputing identical embeddings
- Support configurable cache size
- Track cache statistics

This module is independent of any embedding provider.
"""

from __future__ import annotations

import hashlib
import logging
from collections import OrderedDict
from typing import Sequence

from advisory_engine.config.defaults import EMBEDDING_CACHE_SIZE

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """
    LRU cache for text embeddings.

    Cache Key:
        SHA256(text)

    Cache Value:
        Embedding vector
    """

    def __init__(
        self,
        max_size: int = EMBEDDING_CACHE_SIZE,
    ) -> None:

        self.max_size = max_size

        self._cache: OrderedDict[
            str,
            Sequence[float],
        ] = OrderedDict()

        self.hits = 0
        self.misses = 0

    @staticmethod
    def _hash(text: str) -> str:
        """
        Generate deterministic cache key.
        """

        return hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()

    def get(
        self,
        text: str,
    ) -> Sequence[float] | None:
        """
        Retrieve embedding from cache.
        """

        key = self._hash(text)

        embedding = self._cache.get(key)

        if embedding is None:
            self.misses += 1
            return None

        self.hits += 1

        # LRU refresh
        self._cache.move_to_end(key)

        logger.debug("Embedding cache hit")

        return embedding

    def put(
        self,
        text: str,
        embedding: Sequence[float],
    ) -> None:
        """
        Store embedding in cache.
        """

        key = self._hash(text)

        self._cache[key] = embedding

        self._cache.move_to_end(key)

        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def contains(
        self,
        text: str,
    ) -> bool:
        """
        Check whether embedding exists.
        """

        return self._hash(text) in self._cache

    def clear(self) -> None:
        """
        Clear cache.
        """

        self._cache.clear()

        self.hits = 0
        self.misses = 0

        logger.info("Embedding cache cleared.")

    @property
    def size(self) -> int:
        """
        Current cache size.
        """

        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        """
        Cache hit ratio.
        """

        total = self.hits + self.misses

        if total == 0:
            return 0.0

        return self.hits / total

    def stats(self) -> dict[str, float | int]:
        """
        Return cache statistics.
        """

        return {
            "entries": self.size,
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hit_rate, 4),
        }