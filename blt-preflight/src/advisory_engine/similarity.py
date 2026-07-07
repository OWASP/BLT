"""
similarity.py

Similarity filtering for the BLT Preflight advisory pipeline.

Responsibilities
----------------
- Filter retrieved document chunks
- Apply configurable similarity threshold
- Sort chunks by relevance
- Determine whether retrieval quality is sufficient

This module performs NO vector search.
It only evaluates retrieval results.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


DEFAULT_SIMILARITY_THRESHOLD = 0.60


@dataclass(slots=True)
class SimilarityResult:
    """
    Result returned after similarity filtering.
    """

    accepted_chunks: list[dict[str, Any]]
    rejected_chunks: list[dict[str, Any]]
    highest_score: float
    passed_threshold: bool


class SimilarityEngine:
    """
    Filters retrieval results using similarity scores.
    """

    def __init__(
        self,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> None:

        if not 0.0 <= threshold <= 1.0:
            raise ValueError(
                "Similarity threshold must be between 0 and 1."
            )

        self.threshold = threshold

    def filter_chunks(
        self,
        chunks: list[dict[str, Any]],
    ) -> SimilarityResult:
        """
        Filter chunks below the configured threshold.

        Expected chunk format

        {
            "content": "...",
            "score": 0.81,
            "metadata": {...}
        }
        """

        if not chunks:
            logger.warning("No retrieved chunks received.")

            return SimilarityResult(
                accepted_chunks=[],
                rejected_chunks=[],
                highest_score=0.0,
                passed_threshold=False,
            )

        accepted = []
        rejected = []

        highest = 0.0

        for chunk in chunks:

            score = float(chunk.get("score", 0.0))

            highest = max(highest, score)

            if score >= self.threshold:
                accepted.append(chunk)
            else:
                rejected.append(chunk)

        accepted.sort(
            key=lambda item: item.get("score", 0.0),
            reverse=True,
        )

        logger.info(
            "Similarity filtering complete. %d accepted, %d rejected.",
            len(accepted),
            len(rejected),
        )

        return SimilarityResult(
            accepted_chunks=accepted,
            rejected_chunks=rejected,
            highest_score=highest,
            passed_threshold=len(accepted) > 0,
        )

    def should_fallback(
        self,
        result: SimilarityResult,
    ) -> bool:
        """
        Determine whether the pipeline should use
        the fallback advisory mechanism.
        """

        return not result.passed_threshold

    def top_chunks(
        self,
        result: SimilarityResult,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Return the highest-ranked chunks.

        Default follows the proposal by returning
        the top three retrieved documents.
        """

        return result.accepted_chunks[:limit]

    def update_threshold(
        self,
        threshold: float,
    ) -> None:
        """
        Update similarity threshold at runtime.
        """

        if not 0.0 <= threshold <= 1.0:
            raise ValueError(
                "Similarity threshold must be between 0 and 1."
            )

        logger.info(
            "Updating similarity threshold from %.2f to %.2f",
            self.threshold,
            threshold,
        )

        self.threshold = threshold