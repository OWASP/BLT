"""
validation.py

Validation utilities for retrieved knowledge base chunks.

Responsibilities
----------------
- Validate retrieval output
- Remove invalid chunks
- Remove duplicate chunks
- Validate metadata
- Normalize retrieval structure

This module performs NO similarity calculations and
NO LLM generation.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class RetrievalValidationError(Exception):
    """Raised when retrieval validation fails."""


class RetrievalValidator:
    """
    Validates and sanitizes retrieval results before
    they are passed into the advisory generator.
    """

    REQUIRED_FIELDS = (
        "content",
        "score",
        "metadata",
    )

    def validate(
        self,
        chunks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Validate retrieval output.

        Parameters
        ----------
        chunks
            Raw chunks returned from the retriever.

        Returns
        -------
        list[dict]
            Clean retrieval results.
        """

        if not chunks:
            logger.warning("Retriever returned no chunks.")
            return []

        validated = []
        seen = set()

        for chunk in chunks:

            if not self._has_required_fields(chunk):
                logger.warning(
                    "Skipping chunk with missing fields."
                )
                continue

            content = chunk["content"].strip()

            if not content:
                logger.warning(
                    "Skipping empty chunk."
                )
                continue

            if content in seen:
                logger.debug(
                    "Duplicate chunk removed."
                )
                continue

            seen.add(content)

            chunk["score"] = self._normalize_score(
                chunk["score"]
            )

            chunk["metadata"] = self._normalize_metadata(
                chunk["metadata"]
            )

            validated.append(chunk)

        logger.info(
            "Validated %d retrieval chunks.",
            len(validated),
        )

        return validated

    def _has_required_fields(
        self,
        chunk: dict[str, Any],
    ) -> bool:
        """
        Ensure required fields exist.
        """

        return all(
            field in chunk
            for field in self.REQUIRED_FIELDS
        )

    def _normalize_score(
        self,
        score: Any,
    ) -> float:
        """
        Normalize similarity score.

        Raises
        ------
        RetrievalValidationError
        """

        try:
            score = float(score)

        except (TypeError, ValueError) as exc:
            raise RetrievalValidationError(
                "Invalid similarity score."
            ) from exc

        if score < 0:
            score = 0.0

        if score > 1:
            score = 1.0

        return score

    def _normalize_metadata(
        self,
        metadata: Any,
    ) -> dict[str, Any]:
        """
        Normalize metadata.
        """

        if metadata is None:
            return {}

        if not isinstance(metadata, dict):
            return {}

        return metadata

    def has_results(
        self,
        chunks: list[dict[str, Any]],
    ) -> bool:
        """
        Check whether retrieval produced any
        usable documents.
        """

        return len(chunks) > 0

    def top_chunks(
        self,
        chunks: list[dict[str, Any]],
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Return highest scoring chunks.

        Assumes scores have already been
        normalized.
        """

        return sorted(
            chunks,
            key=lambda c: c["score"],
            reverse=True,
        )[:limit]