"""
test_pipeline.py

End-to-end integration tests for the BLT Preflight advisory pipeline.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from advisory_engine.evaluation.confidence import (
    ConfidenceEvaluator,
    ConfidenceInputs,
)
from advisory_engine.evaluation.evaluator import (
    EvaluationInput,
    PipelineEvaluator,
)
from advisory_engine.gitlab.formatter import (
    GitLabAdvisoryFormatter,
)
from advisory_engine.gitlab.merge_request import (
    MergeRequestContextBuilder,
)
from advisory_engine.gitlab.webhook import (
    GitLabWebhookParser,
)


@pytest.fixture
def webhook_headers():
    return {
        "X-Gitlab-Event": "Merge Request Hook",
    }


@pytest.fixture
def webhook_payload():
    return {
        "project": {
            "id": 1,
            "name": "preflight",
            "path_with_namespace": "owasp/preflight",
            "web_url": "https://gitlab.com/owasp/preflight",
        },
        "user": {
            "username": "alice",
        },
        "object_attributes": {
            "iid": 10,
            "title": "Improve authentication",
            "description": "Adds MFA",
            "source_branch": "feature/mfa",
            "target_branch": "main",
            "action": "open",
        },
        "labels": [
            {
                "title": "security",
            }
        ],
    }


# ---------------------------------------------------------------------
# Pipeline Integration
# ---------------------------------------------------------------------


def test_full_pipeline(
    webhook_headers,
    webhook_payload,
):

    event = GitLabWebhookParser.parse(
        webhook_headers,
        webhook_payload,
    )

    context = MergeRequestContextBuilder.build(
        event,
        changed_files=[
            "src/auth.py",
        ],
    )

    advisory = {
        "severity": "High",
        "category": "Authentication",
        "title": "Password validation missing",
        "explanation": "Weak password validation detected.",
        "recommendation": "Use Argon2.",
    }

    markdown = GitLabAdvisoryFormatter.format(
        advisory
    )

    assert context.contributor_intent
    assert "Password validation" in markdown


# ---------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------


def test_high_confidence():

    result = ConfidenceEvaluator.evaluate(
        ConfidenceInputs(
            similarity_score=0.90,
            retrieval_quality=0.95,
            validation_score=0.98,
        )
    )

    assert result.level == "High"
    assert result.score > 0.80


def test_medium_confidence():

    result = ConfidenceEvaluator.evaluate(
        ConfidenceInputs(
            similarity_score=0.65,
            retrieval_quality=0.70,
            validation_score=0.75,
        )
    )

    assert result.level in {
        "Medium",
        "High",
    }


def test_fallback_penalty():

    normal = ConfidenceEvaluator.evaluate(
        ConfidenceInputs(
            similarity_score=0.90,
            retrieval_quality=0.90,
            validation_score=0.90,
        )
    )

    fallback = ConfidenceEvaluator.evaluate(
        ConfidenceInputs(
            similarity_score=0.90,
            retrieval_quality=0.90,
            validation_score=0.90,
            fallback_used=True,
        )
    )

    assert fallback.score < normal.score


def test_retry_penalty():

    no_retry = ConfidenceEvaluator.evaluate(
        ConfidenceInputs(
            similarity_score=0.8,
            retrieval_quality=0.8,
            validation_score=0.8,
        )
    )

    retry = ConfidenceEvaluator.evaluate(
        ConfidenceInputs(
            similarity_score=0.8,
            retrieval_quality=0.8,
            validation_score=0.8,
            retries=3,
        )
    )

    assert retry.score < no_retry.score


# ---------------------------------------------------------------------
# Evaluation Report
# ---------------------------------------------------------------------


def test_pipeline_report():

    report = PipelineEvaluator.evaluate(
        EvaluationInput(
            similarity_score=0.88,
            retrieval_quality=0.90,
            validation_score=0.95,
            retrieval_time_ms=40,
            generation_time_ms=520,
            validation_time_ms=8,
            total_pipeline_time_ms=568,
            cache_hit=True,
            fallback_used=False,
            retries=0,
            timeout_occurred=False,
        )
    )

    assert report.summary["pipeline_status"] == "Success"

    assert report.summary["cache"] == "Hit"

    assert report.confidence.level == "High"


def test_report_serialization():

    report = PipelineEvaluator.evaluate(
        EvaluationInput(
            similarity_score=0.80,
            retrieval_quality=0.82,
            validation_score=0.90,
            retrieval_time_ms=30,
            generation_time_ms=500,
            validation_time_ms=10,
            total_pipeline_time_ms=540,
            cache_hit=False,
            fallback_used=False,
            retries=1,
            timeout_occurred=False,
        )
    )

    result = PipelineEvaluator.to_dict(
        report
    )

    assert "timestamp" in result
    assert "metrics" in result
    assert "summary" in result
    assert "confidence" in result


# ---------------------------------------------------------------------
# Mock Integration
# ---------------------------------------------------------------------


def test_pipeline_with_mock_generator():

    generator = Mock()

    generator.generate.return_value = {
        "severity": "Medium",
        "title": "Mock advisory",
    }

    advisory = generator.generate()

    markdown = GitLabAdvisoryFormatter.format(
        advisory
    )

    generator.generate.assert_called_once()

    assert "Mock advisory" in markdown


def test_pipeline_with_empty_files(
    webhook_headers,
    webhook_payload,
):

    event = GitLabWebhookParser.parse(
        webhook_headers,
        webhook_payload,
    )

    context = MergeRequestContextBuilder.build(
        event,
        changed_files=[],
    )

    assert context.files_changed == []


def test_pipeline_timeout():

    result = ConfidenceEvaluator.evaluate(
        ConfidenceInputs(
            similarity_score=0.90,
            retrieval_quality=0.90,
            validation_score=0.90,
            timeout_occurred=True,
        )
    )

    assert result.score < 0.90


def test_pipeline_cache_hit():

    report = PipelineEvaluator.evaluate(
        EvaluationInput(
            similarity_score=0.90,
            retrieval_quality=0.90,
            validation_score=0.90,
            retrieval_time_ms=5,
            generation_time_ms=400,
            validation_time_ms=4,
            total_pipeline_time_ms=409,
            cache_hit=True,
            fallback_used=False,
            retries=0,
            timeout_occurred=False,
        )
    )

    assert report.summary["cache"] == "Hit"


def test_pipeline_cache_miss():

    report = PipelineEvaluator.evaluate(
        EvaluationInput(
            similarity_score=0.90,
            retrieval_quality=0.90,
            validation_score=0.90,
            retrieval_time_ms=30,
            generation_time_ms=450,
            validation_time_ms=6,
            total_pipeline_time_ms=486,
            cache_hit=False,
            fallback_used=False,
            retries=0,
            timeout_occurred=False,
        )
    )

    assert report.summary["cache"] == "Miss"


def test_formatter_with_evaluation():

    advisory = {
        "severity": "Medium",
        "title": "Example",
        "metadata": {
            "confidence": 0.91,
            "retrieval": "high",
        },
    }

    markdown = GitLabAdvisoryFormatter.format(
        advisory
    )

    assert "confidence" in markdown
    assert "retrieval" in markdown