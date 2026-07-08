"""
retrieval_cache.py

LRU cache for retrieval results in the BLT Preflight pipeline.

Responsibilities
----------------
- Cache retrieval results
- Reduce repeated vector database lookups
- Track cache performance
- Support configurable TTL

This cache stores retrieved document chunks,
NOT embeddings.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections import OrderedDict
from typing import Any

from advisory_engine.config.defaults import (
    CACHE_TTL_SECONDS,
    RETRIEVAL_CACHE_SIZE,
)

logger = logging.getLogger(__name__)


class RetrievalCache:
    """
    LRU cache for retrieval results.

    Cache Key
    ---------
    SHA256(query)

    Cache Value
    -----------
    {
        "timestamp": float,
        "results": list[dict]
    }
    """

    def __init__(
        self,
        max_size: int = RETRIEVAL_CACHE_SIZE,
        ttl: int = CACHE_TTL_SECONDS,
    ) -> None:

        self.max_size = max_size
        self.ttl = ttl

        self._cache: OrderedDict[
            str,
            dict[str, Any],
        ] = OrderedDict()

        self.hits = 0
        self.misses = 0
        self.expired = 0

    @staticmethod
    def _hash(query: str) -> str:
        """
        Create deterministic cache key.
        """
        return hashlib.sha256(
            query.encode("utf-8")
        ).hexdigest()

    def get(
        self,
        query: str,
    ) -> list[dict[str, Any]] | None:
        """
        Retrieve cached retrieval results.
        """

        key = self._hash(query)

        item = self._cache.get(key)

        if item is None:
            self.misses += 1
            return None

        if time.time() - item["timestamp"] > self.ttl:
            self.expired += 1
            self.misses += 1

            del self._cache[key]

            logger.debug("Retrieval cache expired.")

            return None

        self.hits += 1

        self._cache.move_to_end(key)

        logger.debug("Retrieval cache hit.")

        return item["results"]

    def put(
        self,
        query: str,
        results: list[dict[str, Any]],
    ) -> None:
        """
        Store retrieval results.
        """

        key = self._hash(query)

        self._cache[key] = {
            "timestamp": time.time(),
            "results": results,
        }

        self._cache.move_to_end(key)

        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def invalidate(
        self,
        query: str,
    ) -> None:
        """
        Remove one cache entry.
        """

        self._cache.pop(self._hash(query), None)

    def clear(self) -> None:
        """
        Remove every cached retrieval.
        """

        self._cache.clear()

        self.hits = 0
        self.misses = 0
        self.expired = 0

        logger.info("Retrieval cache cleared.")

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses

        if total == 0:
            return 0.0

        return self.hits / total

    def stats(self) -> dict[str, float | int]:
        """
        Cache statistics.
        """

        return {
            "entries": self.size,
            "max_size": self.max_size,
            "ttl_seconds": self.ttl,
            "hits": self.hits,
            "misses": self.misses,
            "expired": self.expired,
            "hit_rate": round(self.hit_rate, 4),
        }