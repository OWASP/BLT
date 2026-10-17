"""
webhook.py

GitLab webhook parsing utilities for the BLT Preflight pipeline.

Responsibilities
----------------
- Validate incoming GitLab webhook events
- Parse Merge Request webhook payloads
- Normalize webhook data
- Provide a provider-independent interface to the pipeline

This module only parses webhook payloads.
It does not communicate with the GitLab API.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


SUPPORTED_EVENTS = {
    "Merge Request Hook",
}


class UnsupportedWebhookEvent(ValueError):
    """Raised when an unsupported GitLab webhook is received."""


class InvalidWebhookPayload(ValueError):
    """Raised when the webhook payload is malformed."""


@dataclass(slots=True)
class GitLabWebhookEvent:
    """
    Normalized GitLab webhook event.
    """

    event_type: str
    action: str

    project_id: int
    project_name: str
    project_path: str

    repository_url: str

    merge_request_iid: int
    merge_request_title: str
    merge_request_description: str

    source_branch: str
    target_branch: str

    author: str

    labels: list[str]


class GitLabWebhookParser:
    """
    Parse GitLab Merge Request webhook payloads.
    """

    @staticmethod
    def parse(
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> GitLabWebhookEvent:
        """
        Parse a GitLab webhook payload.
        """

        event = headers.get("X-Gitlab-Event")

        if event not in SUPPORTED_EVENTS:
            raise UnsupportedWebhookEvent(
                f"Unsupported GitLab event: {event}"
            )

        try:

            project = payload["project"]
            attributes = payload["object_attributes"]
            user = payload["user"]

            labels = [
                label["title"]
                for label in payload.get("labels", [])
            ]

            return GitLabWebhookEvent(
                event_type=event,

                action=attributes["action"],

                project_id=project["id"],
                project_name=project["name"],
                project_path=project["path_with_namespace"],

                repository_url=project["web_url"],

                merge_request_iid=attributes["iid"],
                merge_request_title=attributes["title"],
                merge_request_description=(
                    attributes.get("description") or ""
                ),

                source_branch=attributes["source_branch"],
                target_branch=attributes["target_branch"],

                author=user["username"],

                labels=labels,
            )

        except KeyError as exc:

            raise InvalidWebhookPayload(
                f"Missing required webhook field: {exc}"
            ) from exc

    @staticmethod
    def is_merge_request_event(
        headers: dict[str, str],
    ) -> bool:
        """
        Determine whether the webhook is a Merge Request event.
        """

        return (
            headers.get("X-Gitlab-Event")
            == "Merge Request Hook"
        )

    @staticmethod
    def should_process(
        event: GitLabWebhookEvent,
    ) -> bool:
        """
        Determine whether the pipeline should process
        the Merge Request.

        Only process creation, updates and reopen events.
        """

        return event.action in {
            "open",
            "update",
            "reopen",
        }