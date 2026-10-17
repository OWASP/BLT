"""
generator.py

Generates structured security advisories using the configured
LLM provider.

Responsibilities
----------------
- Build advisory prompts
- Invoke the configured LLM provider
- Parse structured responses
- Return advisory objects

This module does NOT:
- Retrieve embeddings
- Query ChromaDB
- Compute similarity
- Validate schema
"""

from __future__ import annotations

import logging
from typing import Any

from advisory_engine.pipeline.context_builder import AdvisoryContext
from advisory_engine.rag.schema import AdvisorySchema
from advisory_engine.rag.prompt_template import build_advisory_prompt

logger = logging.getLogger(__name__)


class AdvisoryGenerationError(Exception):
    """Raised when advisory generation fails."""


class AdvisoryGenerator:
    """
    Generates structured advisories from
    retrieved OWASP documentation.
    """

    def __init__(self, llm_provider: Any) -> None:
        """
        Parameters
        ----------
        llm_provider

        Configured provider (Gemini, Ollama, etc.)
        implementing a generate(prompt: str) interface.
        """

        self.provider = llm_provider

    def generate(
        self,
        *,
        context: AdvisoryContext,
        retrieved_chunks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Generate a structured advisory.

        Parameters
        ----------
        context
            Normalized advisory context.

        retrieved_chunks
            Relevant OWASP chunks after retrieval
            and similarity filtering.
        """

        logger.info(
            "Generating advisory for repository '%s'",
            context.repository,
        )

        prompt = build_advisory_prompt(
            context=context,
            retrieved_chunks=retrieved_chunks,
        )

        try:
            response = self.provider.generate(prompt)

        except Exception as exc:
            logger.exception("LLM generation failed")
            raise AdvisoryGenerationError(str(exc)) from exc

        advisory = self._parse_response(response)

        logger.info(
            "Generated advisory with severity '%s'",
            advisory.get("severity", "UNKNOWN"),
        )

        return advisory

    def _parse_response(
        self,
        response: Any,
    ) -> dict[str, Any]:
        """
        Convert provider response into
        AdvisorySchema dictionary.
        """

        if isinstance(response, AdvisorySchema):
            return response.model_dump()

        if isinstance(response, dict):
            return response

        raise AdvisoryGenerationError(
            "Provider returned unsupported response type."
        )