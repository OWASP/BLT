"""
context_builder.py

Builds a normalized advisory context for the BLT Preflight
pipeline.

This module is intentionally provider-neutral and currently
targets GitLab Merge Request events and local execution
(VS Code / pre-commit).

Responsibilities
----------------
- Normalize incoming metadata
- Collect changed files
- Collect labels
- Collect merge request metadata
- Produce a single AdvisoryContext object

No retrieval, LLM or advisory generation logic belongs here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AdvisoryContext:
    """
    Canonical context object shared by the entire
    advisory pipeline.

    Every stage consumes this object instead of
    raw GitLab payloads.
    """

    repository: str

    branch: str

    changed_files: list[str] = field(default_factory=list)

    labels: list[str] = field(default_factory=list)

    commit_message: str = ""

    merge_request_title: str = ""

    merge_request_id: int | None = None

    author: str = ""

    event_name: str = ""

    metadata: dict[str, Any] = field(default_factory=dict)


class ContextBuilder:
    """
    Creates AdvisoryContext objects from GitLab events
    or local execution.

    Supported sources
    -----------------
    • GitLab Merge Request pipeline
    • VS Code Extension
    • Pre-Commit Hook
    • CLI
    """

    @staticmethod
    def from_gitlab_event(payload: dict[str, Any]) -> AdvisoryContext:
        """
        Build context from a GitLab Merge Request event.

        The payload is expected to contain normalized fields
        supplied by the GitLab integration layer.
        """

        return AdvisoryContext(
            repository=payload.get("repository", ""),
            branch=payload.get("branch", ""),
            changed_files=payload.get("changed_files", []),
            labels=payload.get("labels", []),
            commit_message=payload.get("commit_message", ""),
            merge_request_title=payload.get("merge_request_title", ""),
            merge_request_id=payload.get("merge_request_id"),
            author=payload.get("author", ""),
            event_name=payload.get("event_name", "merge_request"),
            metadata=payload,
        )

    @staticmethod
    def from_local(
        *,
        repository: str,
        branch: str,
        changed_files: list[str],
        commit_message: str = "",
        labels: list[str] | None = None,
    ) -> AdvisoryContext:
        """
        Build context for local execution.

        Used by:
        - VS Code Extension
        - Pre-Commit Hook
        - Local CLI
        """

        return AdvisoryContext(
            repository=repository,
            branch=branch,
            changed_files=sorted(set(changed_files)),
            labels=labels or [],
            commit_message=commit_message,
            event_name="local",
        )

    @staticmethod
    def update_changed_files(
        context: AdvisoryContext,
        files: list[str],
    ) -> AdvisoryContext:
        """
        Update changed files after SCM inspection.
        """

        context.changed_files = sorted(set(files))
        return context

    @staticmethod
    def add_metadata(
        context: AdvisoryContext,
        **kwargs: Any,
    ) -> AdvisoryContext:
        """
        Attach additional metadata without modifying
        the public schema.
        """

        context.metadata.update(kwargs)
        return context

    @staticmethod
    def to_dict(context: AdvisoryContext) -> dict[str, Any]:
        """
        Convert AdvisoryContext into a serializable
        dictionary.
        """

        return {
            "repository": context.repository,
            "branch": context.branch,
            "changed_files": context.changed_files,
            "labels": context.labels,
            "commit_message": context.commit_message,
            "merge_request_title": context.merge_request_title,
            "merge_request_id": context.merge_request_id,
            "author": context.author,
            "event_name": context.event_name,
            "metadata": context.metadata,
        }