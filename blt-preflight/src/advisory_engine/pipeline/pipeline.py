"""
pipeline.py

Main orchestration pipeline for BLT Preflight.

Responsibilities
----------------
1. Validate incoming advisory context
2. Retrieve relevant OWASP knowledge
3. Validate retrieval quality
4. Apply similarity threshold
5. Generate advisory
6. Validate advisory schema
7. Return final advisory

This module intentionally contains no business logic.
Each stage is delegated to a dedicated component.
"""

from __future__ import annotations

import logging
from typing import Any

from advisory_engine.pipeline.context_builder import AdvisoryContext
from advisory_engine.rag.retriever import Retriever
from advisory_engine.rag.similarity import SimilarityEngine
from advisory_engine.rag.validation import RetrievalValidator
from advisory_engine.advisory.generator import AdvisoryGenerator
from advisory_engine.advisory.schema_validator import SchemaValidator

logger = logging.getLogger(__name__)


class AdvisoryPipeline:
    """
    Coordinates the complete advisory generation workflow.
    
    
    """

    def __init__(
        self,
        retriever: Retriever,
        generator: AdvisoryGenerator,
        similarity_engine: SimilarityEngine,
        retrieval_validator: RetrievalValidator,
        schema_validator: SchemaValidator,
    ) -> None:

        self.retriever = retriever
        self.generator = generator
        self.similarity_engine = similarity_engine
        self.retrieval_validator = retrieval_validator
        self.schema_validator = schema_validator

    def run(
        self,
        context: AdvisoryContext,
    ) -> dict[str, Any]:
        """
        Execute the complete advisory pipeline.

        Parameters
        ----------
        context:
            Normalized advisory context.

        Returns
        -------
        dict
            Structured advisory.
        """

        logger.info("Starting advisory pipeline")

        retrieved_chunks = self.retriever.retrieve(context)

        validated_chunks = self.retrieval_validator.validate(
            retrieved_chunks
        )

        relevant_chunks = self.similarity_engine.filter_chunks(
            validated_chunks
        )

        advisory = self.generator.generate(
            context=context,
            retrieved_chunks=relevant_chunks,
        )

        validated_advisory = self.schema_validator.validate(
            advisory
        )

        logger.info("Advisory pipeline completed successfully")

        return validated_advisory