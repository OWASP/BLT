"""
merge_request.py

GitLab Merge Request integration for the BLT Preflight pipeline.

Responsibilities
----------------
- Convert GitLab Merge Request events into AdvisoryContext
- Normalize Merge Request metadata
- Preserve repository information
- Prepare data for the advisory pipeline

This module does not call the GitLab REST API.
It only transforms already available Merge Request data.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from advisory_engine.pipeline.context_builder import (
    AdvisoryContext,
)

from advisory_engine.gitlab.webhook import (
    GitLabWebhookEvent,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MergeRequestMetadata:
    """
    Normalized Merge Request metadata.
    """

    project_id: int
    project_name: str
    project_path: str

    repository_url: str

    merge_request_iid: int
    title: str
    description: str

    source_branch: str
    target_branch: str

    author: str

    labels: list[str] = field(default_factory=list)

    changed_files: list[str] = field(default_factory=list)


class MergeRequestContextBuilder:
    """
    Builds AdvisoryContext objects from GitLab Merge Requests.
    """

    @staticmethod
    def build(
        event: GitLabWebhookEvent,
        *,
        changed_files: list[str] | None = None,
    ) -> AdvisoryContext:
        """
        Convert a GitLab webhook event into an AdvisoryContext.
        """

        metadata = MergeRequestMetadata(
            project_id=event.project_id,
            project_name=event.project_name,
            project_path=event.project_path,
            repository_url=event.repository_url,
            merge_request_iid=event.merge_request_iid,
            title=event.merge_request_title,
            description=event.merge_request_description,
            source_branch=event.source_branch,
            target_branch=event.target_branch,
            author=event.author,
            labels=event.labels,
            changed_files=changed_files or [],
        )

        logger.info(
            "Building AdvisoryContext for MR !%s",
            metadata.merge_request_iid,
        )

        return AdvisoryContext(
            contributor_intent=metadata.title,
            files_changed=metadata.changed_files,
            labels=metadata.labels,
            metadata={
                "gitlab": {
                    "project_id": metadata.project_id,
                    "project_name": metadata.project_name,
                    "project_path": metadata.project_path,
                    "repository_url": metadata.repository_url,
                    "merge_request_iid": metadata.merge_request_iid,
                    "source_branch": metadata.source_branch,
                    "target_branch": metadata.target_branch,
                    "author": metadata.author,
                    "description": metadata.description,
                }
            },
        )

    @staticmethod
    def summary(
        metadata: MergeRequestMetadata,
    ) -> dict[str, Any]:
        """
        Return a lightweight Merge Request summary.
        """

        return {
            "project": metadata.project_path,
            "merge_request": metadata.merge_request_iid,
            "title": metadata.title,
            "author": metadata.author,
            "source_branch": metadata.source_branch,
            "target_branch": metadata.target_branch,
            "labels": metadata.labels,
            "changed_files": len(metadata.changed_files),
        }