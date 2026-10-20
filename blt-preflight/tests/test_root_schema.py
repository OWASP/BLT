"""Root schema.py must import and re-export the canonical RAG models."""

import pytest
from pydantic import ValidationError

import schema as root_schema
from advisory_engine.rag.schema import Advisory as CanonicalAdvisory
from advisory_engine.rag.schema import Severity as CanonicalSeverity


def test_root_reexports_canonical_advisory():
    assert root_schema.Advisory is CanonicalAdvisory
    assert root_schema.Severity is CanonicalSeverity
    assert root_schema.Severity.HIGH.value == "HIGH"
    assert not hasattr(root_schema.Severity, "HIGHT")


def test_root_schema_rejects_empty_recommendations():
    with pytest.raises(ValidationError):
        root_schema.Advisory(
            severity="LOW",
            category="INFO",
            explanation="Documentation-only change with no security surface in this merge request.",
            recommendations=["", "  "],
        )


def test_root_schema_accepts_valid_payload():
    adv = root_schema.Advisory(
        severity=root_schema.Severity.HIGH,
        category="A07:2021",
        explanation="Session handling changed. Confirm cookie flags, rotation, and lockout before merge.",
        recommendations=["Set HttpOnly and Secure on session cookies"],
    )
    assert adv.explanation.startswith("Session")
