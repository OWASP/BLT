"""Canonical advisory schema for the RAG / LLM path.

Define models here. Do not import this module from itself.
The repository-root schema.py re-exports these names.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class Reference(BaseModel):
    title: str
    category: str = ""
    url: str


class Advisory(BaseModel):
    severity: Severity
    category: str = Field(..., description="Primary OWASP category triggered")
    explanation: str = Field(..., min_length=20, max_length=800)
    recommendations: List[str] = Field(..., min_length=1, max_length=6)
    references: List[Reference] = Field(default_factory=list)
    title: Optional[str] = None
    source: str = Field(
        default="static_fallback",
        description="'rag' | 'static_fallback'",
    )
    average_retrieval_quality: Optional[float] = None
    generation_time_ms: Optional[int] = None

    @field_validator("recommendations")
    @classmethod
    def no_empty_recommendations(cls, v: List[str]) -> List[str]:
        cleaned = [r.strip() for r in v if r and r.strip()]
        if not cleaned:
            raise ValueError("recommendations must contain at least one non-empty entry")
        return cleaned

    @field_validator("explanation")
    @classmethod
    def explanation_length(cls, v: str) -> str:
        text = v.strip()
        if len(text.split()) < 5:
            raise ValueError("explanation too short / not substantive")
        return text


AdvisorySchema = Advisory


class StructuredAdvisory(BaseModel):
    """Top-level response returned by POST /advisory."""

    status: str
    advisory: Optional[Advisory] = None
    retrieved_knowledge_base_chunks: int = 0
    message: Optional[str] = None


__all__ = [
    "Advisory",
    "AdvisorySchema",
    "Reference",
    "Severity",
    "StructuredAdvisory",
]
