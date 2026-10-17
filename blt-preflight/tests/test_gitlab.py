"""
test_gitlab.py

Tests for GitLab integration components.
"""

from __future__ import annotations

import pytest

from advisory_engine.gitlab.webhook import (
    GitLabWebhookParser,
    UnsupportedWebhookEvent,
    InvalidWebhookPayload,
)

from advisory_engine.gitlab.merge_request import (
    MergeRequestContextBuilder,
)

from advisory_engine.gitlab.formatter import (
    GitLabAdvisoryFormatter,
)


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def webhook_headers():
    return {
        "X-Gitlab-Event": "Merge Request Hook",
    }


@pytest.fixture
def webhook_payload():
    return {
        "project": {
            "id": 100,
            "name": "preflight",
            "path_with_namespace": "owasp/preflight",
            "web_url": "https://gitlab.com/owasp/preflight",
        },
        "user": {
            "username": "alice",
        },
        "object_attributes": {
            "iid": 5,
            "title": "Improve authentication",
            "description": "Adds MFA support",
            "source_branch": "feature/mfa",
            "target_branch": "main",
            "action": "open",
        },
        "labels": [
            {
                "title": "security",
            },
            {
                "title": "authentication",
            },
        ],
    }


# ---------------------------------------------------------------------
# Webhook Parser
# ---------------------------------------------------------------------


def test_parse_webhook(
    webhook_headers,
    webhook_payload,
):

    event = GitLabWebhookParser.parse(
        webhook_headers,
        webhook_payload,
    )

    assert event.project_id == 100
    assert event.author == "alice"
    assert event.merge_request_iid == 5
    assert event.labels == [
        "security",
        "authentication",
    ]


def test_is_merge_request_event(
    webhook_headers,
):

    assert GitLabWebhookParser.is_merge_request_event(
        webhook_headers
    )


def test_should_process_open_event(
    webhook_headers,
    webhook_payload,
):

    event = GitLabWebhookParser.parse(
        webhook_headers,
        webhook_payload,
    )

    assert GitLabWebhookParser.should_process(
        event
    )


@pytest.mark.parametrize(
    "action",
    [
        "update",
        "reopen",
    ],
)
def test_supported_actions(
    webhook_headers,
    webhook_payload,
    action,
):

    webhook_payload["object_attributes"][
        "action"
    ] = action

    event = GitLabWebhookParser.parse(
        webhook_headers,
        webhook_payload,
    )

    assert GitLabWebhookParser.should_process(
        event
    )


@pytest.mark.parametrize(
    "action",
    [
        "close",
        "merge",
        "approved",
    ],
)
def test_unsupported_actions(
    webhook_headers,
    webhook_payload,
    action,
):

    webhook_payload["object_attributes"][
        "action"
    ] = action

    event = GitLabWebhookParser.parse(
        webhook_headers,
        webhook_payload,
    )

    assert (
        GitLabWebhookParser.should_process(
            event
        )
        is False
    )


def test_invalid_event(
    webhook_payload,
):

    with pytest.raises(
        UnsupportedWebhookEvent
    ):
        GitLabWebhookParser.parse(
            {
                "X-Gitlab-Event": "Push Hook",
            },
            webhook_payload,
        )


def test_missing_payload_field(
    webhook_headers,
    webhook_payload,
):

    del webhook_payload["project"]

    with pytest.raises(
        InvalidWebhookPayload
    ):
        GitLabWebhookParser.parse(
            webhook_headers,
            webhook_payload,
        )


# ---------------------------------------------------------------------
# Merge Request Context
# ---------------------------------------------------------------------


def test_context_builder(
    webhook_headers,
    webhook_payload,
):

    event = GitLabWebhookParser.parse(
        webhook_headers,
        webhook_payload,
    )

    context = (
        MergeRequestContextBuilder.build(
            event,
            changed_files=[
                "src/auth.py",
                "src/login.py",
            ],
        )
    )

    assert (
        context.contributor_intent
        == "Improve authentication"
    )

    assert len(
        context.files_changed
    ) == 2

    assert (
        context.metadata["gitlab"][
            "author"
        ]
        == "alice"
    )


def test_context_without_files(
    webhook_headers,
    webhook_payload,
):

    event = GitLabWebhookParser.parse(
        webhook_headers,
        webhook_payload,
    )

    context = (
        MergeRequestContextBuilder.build(
            event
        )
    )

    assert context.files_changed == []


def test_summary(
    webhook_headers,
    webhook_payload,
):

    event = GitLabWebhookParser.parse(
        webhook_headers,
        webhook_payload,
    )

    metadata = (
        MergeRequestContextBuilder.build(
            event
        ).metadata["gitlab"]
    )

    assert metadata["project_name"] == "preflight"


# ---------------------------------------------------------------------
# Formatter
# ---------------------------------------------------------------------


def test_markdown_formatter():

    advisory = {
        "severity": "High",
        "category": "Authentication",
        "title": "Weak Password Policy",
        "explanation": "Passwords are weak.",
        "recommendation": "Use Argon2.",
        "references": [
            "OWASP Authentication Cheat Sheet",
        ],
    }

    markdown = (
        GitLabAdvisoryFormatter.format(
            advisory
        )
    )

    assert (
        "BLT Preflight Security Advisory"
        in markdown
    )

    assert "High" in markdown
    assert "Authentication" in markdown
    assert "Use Argon2." in markdown


def test_error_formatter():

    markdown = (
        GitLabAdvisoryFormatter.format_error(
            "Pipeline failed."
        )
    )

    assert "Pipeline failed." in markdown


def test_fallback_formatter():

    advisory = {
        "severity": "Low",
        "title": "Example",
    }

    markdown = (
        GitLabAdvisoryFormatter.format_fallback(
            advisory
        )
    )

    assert "fallback" in markdown.lower()


def test_empty_advisory():

    markdown = (
        GitLabAdvisoryFormatter.format(
            {}
        )
    )

    assert (
        "BLT Preflight Security Advisory"
        in markdown
    )


def test_reference_rendering():

    advisory = {
        "references": [
            "OWASP Top 10",
            "OWASP ASVS",
        ]
    }

    markdown = (
        GitLabAdvisoryFormatter.format(
            advisory
        )
    )

    assert "- OWASP Top 10" in markdown
    assert "- OWASP ASVS" in markdown


def test_metadata_rendering():

    advisory = {
        "metadata": {
            "confidence": 0.92,
            "retrieval": "high",
        }
    }

    markdown = (
        GitLabAdvisoryFormatter.format(
            advisory
        )
    )

    assert "confidence" in markdown
    assert "retrieval" in markdown