"""Ingestion layer: GitLab webhook helpers.

Phase 2 will add poller functions for BLT and GitLab gap detection.
"""

from .gitlab_webhook import verify_gitlab_signature, parse_event_type

__all__ = [
    "verify_gitlab_signature",
    "parse_event_type",
]
