"""
Core Tool Implementations and Utility Helpers for the BLT-MCP Server.

This module provides common utility helper functions and primary execution logic used by MCP tool handlers.

Key Functions:
- `generate_ai_metadata(tool_name: str) -> Dict[str, Any]`: Computes standard timestamp headers and logs
  metadata details to identify write transactions generated or initiated by an AI Agent.
- `summarize_issue_context_impl(issue_id: str, fetch_fn: Callable) -> str`: Orchestrates retrieving raw issue details
  and discussion threads (comments) from the API, formatting the information into a structured text report.

Design Notes:
- Divides tools registration from core logic to facilitate unit testing (mocking network request wrappers).
- Structures issue metadata summaries cleanly to fit within standard LLM prompt context windows.
"""

import datetime
import json
import logging
import re
import urllib.parse
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("blt-mcp.tools")


def generate_ai_metadata(tool_name: str) -> dict[str, Any]:
    """
    Generate AI metadata for write operations and log the operation.
    """
    timestamp = datetime.datetime.now(datetime.UTC).isoformat()
    metadata = {"ai_generated": True, "timestamp": timestamp, "source": "BLT-MCP"}
    logger.info(f"Tagged write operation '{tool_name}' with AI metadata: {metadata}")
    return metadata


async def summarize_issue_context_impl(
    issue_id: str, fetch_fn: Callable[[str, str | None], Any]
) -> str:
    """
    Core implementation of the summarize_issue_context tool.
    Accepts issue_id and a fetch function (to query the BLT API).
    """
    logger.info(f"Summarizing context for issue: {issue_id}")
    # Validate issue_id format and sanitize for safe URL path construction
    issue_id = str(issue_id).strip()
    if not issue_id or re.search(r"[/?#&]", issue_id):
        return f"Error: Invalid issue ID '{issue_id}'."
    safe_id = urllib.parse.quote(issue_id, safe="")
    try:
        try:
            # Fetch issue details
            issue_raw = await fetch_fn(f"/bugs/{safe_id}", f"issue {issue_id}")
            issue_data = json.loads(issue_raw)
        except Exception as e:
            logger.error(f"Failed to fetch issue {issue_id}: {e}")
            return f"Error: Issue with ID '{issue_id}' not found or could not be retrieved."

        title = issue_data.get("title", "No Title")
        status = issue_data.get("status") or issue_data.get("state") or "Unknown"
        description = (
            issue_data.get("description")
            or issue_data.get("body")
            or "No description provided."
        )

        # Fetch comments - either from issue_data if present, or from the comments endpoint
        comments = issue_data.get("comments")
        if comments is None:
            try:
                comments_raw = await fetch_fn(
                    f"/bugs/{safe_id}/comments", f"comments for issue {issue_id}"
                )
                comments = json.loads(comments_raw)
            except Exception as e:
                logger.warning(f"Failed to fetch comments for issue {issue_id}: {e}")
                comments = None  # Preserve unavailable state distinct from empty

        # Format comments
        comments_formatted = ""
        if comments is None:
            comments_formatted = "Comments unavailable (failed to retrieve)."
        elif isinstance(comments, list) and len(comments) > 0:
            formatted_list = []
            for c in comments:
                if isinstance(c, dict):
                    text = (
                        c.get("content")
                        or c.get("body")
                        or c.get("comment_text")
                        or c.get("text")
                        or str(c)
                    )
                    author = (
                        c.get("author")
                        or c.get("username")
                        or c.get("created_by")
                        or "Unknown"
                    )
                    formatted_list.append(f"- {author}: {text}")
                else:
                    formatted_list.append(f"- {c}")
            comments_formatted = "\n".join(formatted_list)
        else:
            comments_formatted = "No comments."

        summary = (
            f"Issue ID: {issue_id}\n"
            f"Title: {title}\n"
            f"Status: {status}\n\n"
            f"Description:\n{description}\n\n"
            f"Comments:\n{comments_formatted}"
        )
        return summary
    except Exception as e:
        logger.error(f"Error generating summary for issue {issue_id}: {e}")
        return f"Error: Failed to generate summary for issue '{issue_id}' due to an internal error."
