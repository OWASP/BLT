"""
GitLab REST API client for OWASP BLT-Toasty.

Posts duplicate-detection comments and applies labels to GitLab issues.
All API calls include rate-limit header checking to respect GitLab's
``RateLimit-Remaining`` header.

Runtime notes
-------------
* Uses the same Pyodide-safe ``fetch`` / ``AbortController`` pattern
  as ``llm_client.py`` and ``embedding_client.py``.
* A hard **10-second timeout** is enforced on every GitLab API call.
"""

from __future__ import annotations

import json
import logging

from src.errors import GitLabAPIError

logger = logging.getLogger("toasty.gitlab_linker")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GITLAB_API_BASE = "https://gitlab.com/api/v4"
RATE_LIMIT_FLOOR = 100
GITLAB_TIMEOUT_SECONDS = 10

# ---------------------------------------------------------------------------
# Pyodide-safe imports
# ---------------------------------------------------------------------------

try:
    from js import AbortController, fetch  # type: ignore[import-not-found]
except ImportError:
    fetch = None  # type: ignore[assignment]
    AbortController = None  # type: ignore[assignment, misc]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _check_rate_limit(response) -> bool:
    """Check GitLab rate-limit headers.

    Args:
        response: The fetch Response object.

    Returns:
        ``True`` if it is safe to proceed (remaining ≥ RATE_LIMIT_FLOOR),
        ``False`` if the caller should back off.
    """
    try:
        remaining_header = response.headers.get("RateLimit-Remaining")
        if remaining_header is not None:
            remaining = int(remaining_header)
            if remaining < RATE_LIMIT_FLOOR:
                logger.warning(
                    "GitLab rate limit low: %d remaining (floor=%d) — backing off",
                    remaining,
                    RATE_LIMIT_FLOOR,
                )
                return False
    except (ValueError, TypeError, AttributeError):
        # If we can't parse the header, proceed cautiously.
        pass
    return True


async def _gitlab_fetch(url: str, options: dict, env) -> object:
    """Execute a rate-limit-aware fetch to the GitLab API.

    Args:
        url: The full GitLab API URL.
        options: The fetch options dict (method, headers, body, signal).
        env: Cloudflare Worker environment for mock injection.

    Returns:
        The fetch Response object.

    Raises:
        GitLabAPIError: On timeout or network failure.
    """
    _fetch = fetch
    _abort_controller_cls = AbortController

    if _fetch is None:
        _fetch = getattr(env, "_fetch_impl", None)
    if _abort_controller_cls is None:
        _abort_controller_cls = getattr(env, "_abort_controller_cls", None)

    if _fetch is None or _abort_controller_cls is None:
        raise RuntimeError("fetch/AbortController unavailable and no mock provided via env")

    controller = _abort_controller_cls.new()
    try:
        from js import setTimeout  # type: ignore[import-not-found]

        setTimeout(lambda: controller.abort(), GITLAB_TIMEOUT_SECONDS * 1000)
    except ImportError:
        pass

    options["signal"] = controller.signal

    try:
        response = await _fetch(url, options)
    except Exception as exc:
        error_msg = str(exc)
        if "abort" in error_msg.lower():
            raise GitLabAPIError(
                f"GitLab API timed out after {GITLAB_TIMEOUT_SECONDS}s",
                status_code=408,
            ) from exc
        raise GitLabAPIError(
            f"GitLab API unreachable: {exc}",
            status_code=503,
        ) from exc

    return response


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def post_duplicate_comment(
    access_token: str,
    project_id: int,
    issue_iid: int,
    duplicate_of_iid: int,
    confidence: float,
    rationale: str,
    env,
) -> bool:
    """Post a duplicate-detection comment on a GitLab issue.

    The comment is formatted as a structured Toasty triage notification.
    Human approval is required — this is informational only.

    Args:
        access_token: GitLab personal or project access token.
        project_id: The numeric GitLab project ID.
        issue_iid: The issue IID to comment on.
        duplicate_of_iid: The IID of the suspected original issue.
        confidence: Duplicate confidence score (0.0–1.0).
        rationale: Human-readable explanation from the detector.
        env: Cloudflare Worker environment for fetch mock injection.

    Returns:
        ``True`` if the comment was posted successfully.
        ``False`` if the request was suppressed due to rate limiting.

    Raises:
        GitLabAPIError: On non-201 HTTP response.
    """
    url = f"{GITLAB_API_BASE}/projects/{project_id}/issues/{issue_iid}/notes"

    comment_body = (
        f"\U0001f916 **Toasty Triage:** This issue may be a duplicate of #{duplicate_of_iid}.\n\n"
        f"**Confidence:** {confidence:.0%}\n\n"
        f"**Rationale:** {rationale}\n\n"
        f"*Please review and confirm or dismiss.*"
    )

    body = json.dumps({"body": comment_body})

    response = await _gitlab_fetch(
        url,
        {
            "method": "POST",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            "body": body,
        },
        env,
    )

    if not _check_rate_limit(response):
        logger.warning(
            "Rate limit exceeded — duplicate comment NOT posted for issue %d",
            issue_iid,
        )
        return False

    status = response.status
    if status != 201:
        error_body = await response.text()
        raise GitLabAPIError(
            f"GitLab POST /notes returned HTTP {status}: {error_body}",
            status_code=status,
        )

    logger.info(
        "Posted duplicate comment on project %d issue %d (duplicate of #%d)",
        project_id,
        issue_iid,
        duplicate_of_iid,
    )
    return True


async def add_duplicate_label(
    access_token: str,
    project_id: int,
    issue_iid: int,
    env,
) -> bool:
    """Add the ``possible-duplicate`` label to a GitLab issue.

    Args:
        access_token: GitLab personal or project access token.
        project_id: The numeric GitLab project ID.
        issue_iid: The issue IID to label.
        env: Cloudflare Worker environment for fetch mock injection.

    Returns:
        ``True`` if the label was added successfully.
        ``False`` if the request was suppressed due to rate limiting.

    Raises:
        GitLabAPIError: On non-200 HTTP response.
    """
    url = f"{GITLAB_API_BASE}/projects/{project_id}/issues/{issue_iid}"

    body = json.dumps({"add_labels": "possible-duplicate"})

    response = await _gitlab_fetch(
        url,
        {
            "method": "PUT",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            "body": body,
        },
        env,
    )

    if not _check_rate_limit(response):
        logger.warning(
            "Rate limit exceeded — duplicate label NOT added for issue %d",
            issue_iid,
        )
        return False

    status = response.status
    if status != 200:
        error_body = await response.text()
        raise GitLabAPIError(
            f"GitLab PUT /issues returned HTTP {status}: {error_body}",
            status_code=status,
        )

    logger.info(
        "Added 'possible-duplicate' label to project %d issue %d",
        project_id,
        issue_iid,
    )
    return True
