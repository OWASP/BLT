"""
Main OWASP BLT Model Context Protocol (MCP) Server Implementation.

This module sets up the primary FastMCP server instance and registers various resource and tool endpoints.
It enables LLMs (Large Language Models) to interact with the OWASP BLT vulnerability database.

Key Offerings:
- **V1 Resources**:
  - `blt://repos`: Retrieves the list of tracked repositories.
  - `blt://issues`: Retrieves the global list of reported bugs/vulnerabilities.
  - `blt://stats`: Retrieves global statistics.
  - `blt://repos/{repo_id}/issues`: Retrieves issues in a specific repository.
  - `blt://issues/{issue_id}`: Retrieves details for a specific bug ID.
  - `blt://good-first-issues`: Open 'good first issue' issues from the git.owaspblt.org issue ledger.
- **V1 Tools**:
  - `submit_issue`: Submits a new bug report to the OWASP BLT platform (requires confirmation).
  - `summarize_issue_context`: Generates a formatted text summary of an issue's context.
  - `triage_vulnerability`: Integrates with Cloudflare Workers AI (Llama 3) to analyze, categorize, and prioritize issues.
  - `draft_vision_issue`: Uses Cloudflare Vision AI (LLaVA) to draft bug reports from local screenshot image files.

Design Details:
- Integrates modular V2 resource routes (`blt_mcp.v2_resources`), V2 write operations (`blt_mcp.v2_tools`), and Prompts (`blt_mcp.prompts`).
- Wraps `sys.stdin` with `StdinWrapper` and `InterceptingStdinBuffer` to intercept and validate JSON-RPC parameters
  before letting the FastMCP server parse the requests.

Entry Point:
- `main()`: Resolves stdin wrappers and launches the core `mcp.run()` event loop.
"""

import asyncio
import hmac
import json
import os
import sys
import tempfile
from pathlib import Path

import anyio
import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Import v2 modular resources, tools and prompts to register them on the mcp instance
import blt_mcp.prompts  # noqa: F401
from blt_mcp import forge_issues, server_base, v2_resources, v2_tools  # noqa: F401
from blt_mcp.server_base import _fetch, logger, mcp
from blt_mcp.tools import generate_ai_metadata, summarize_issue_context_impl
from blt_mcp.validation import InterceptingStdinBuffer, StdinWrapper
from blt_mcp.vision import build_vision_prompt, parse_vision_response

GOOD_FIRST_ISSUE = "good first issue"

# --- Image validation constants and helper ---

ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def _validate_image_path(image_path: str) -> Path:
    """Resolve image_path and confirm it is an allowed image under the approved root, cache, or temp directory."""
    approved_root = (
        Path(os.getenv("BLT_APPROVED_ROOT") or os.getcwd()).expanduser().resolve()
    )
    blt_cache_root = (Path.home() / ".blt-mcp").resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()

    try:
        resolved_path = Path(image_path).expanduser().resolve()
    except Exception as e:
        raise ValueError(f"Invalid image path: {image_path}") from e

    allowed_roots = (approved_root, blt_cache_root, temp_root)
    is_allowed = False
    for root in allowed_roots:
        try:
            resolved_path.relative_to(root)
            is_allowed = True
            break
        except ValueError:
            continue

    if not is_allowed:
        raise ValueError(
            "Access denied: Path is outside the approved root directory."
        )

    if not resolved_path.is_file():
        raise ValueError(
            f"Image file not found at {image_path} (resolved as: {resolved_path})"
        )
    if resolved_path.suffix.lower() not in ALLOWED_IMAGE_EXTS:
        raise ValueError("Invalid image type. Allowed: png, jpg, jpeg, gif, webp")
    if resolved_path.stat().st_size > MAX_IMAGE_BYTES:
        raise ValueError("Image file exceeds maximum size of 10MB")

    return resolved_path


# --- Original V1 Resources ---


@mcp.resource("blt://repos")
async def list_repos() -> str:
    """Get the list of tracked repositories on BLT."""
    logger.info("Fetching repositories list")
    return await _fetch("/repos", context="repos")


@mcp.resource("blt://issues")
async def list_issues() -> str:
    """Get the list of all BLT issues."""
    logger.info("Fetching issues list from BLT API")
    return await _fetch("/bugs", context="issues")


@mcp.resource("blt://stats")
async def get_stats() -> str:
    """Get global statistics for OWASP BLT (e.g., total issues, active repos)."""
    logger.info("Fetching global stats")
    return await _fetch("/stats", context="stats")


@mcp.resource("blt://repos/{repo_id}/issues")
async def list_repo_issues(repo_id: str) -> str:
    """Get the list of issues for a specific repository."""
    logger.info(f"Fetching issues for repository: {repo_id}")
    return await _fetch(
        f"/bugs?repo_id={repo_id}", context=f"issues for repo {repo_id}"
    )


@mcp.resource("blt://issues/{issue_id}")
async def get_issue(issue_id: str) -> str:
    """Get details for a specific BLT issue."""
    return await _fetch(f"/bugs/{issue_id}", context=f"issue {issue_id}")


@mcp.resource("blt://good-first-issues")
async def list_good_first_issues() -> str:
    """Open issues labelled 'good first issue' on git.owaspblt.org, across all BLT folders."""
    try:
        async with httpx.AsyncClient() as client:
            records = await forge_issues.cached_issues(client)
        results = []
        for issue in records:
            if not forge_issues.is_open(issue) or GOOD_FIRST_ISSUE not in forge_issues.labels(issue):
                continue
            folders = forge_issues.issue_projects(issue)
            description = forge_issues.body(issue)
            results.append(
                {
                    "id": int(issue.get("number") or 0),
                    "number": int(issue.get("number") or 0),
                    "title": issue.get("title"),
                    "folder": folders[0] if folders else None,
                    "folders": folders,
                    "repository": folders[0] if folders else "BLT",
                    "labels": forge_issues.labels(issue),
                    "web_url": forge_issues.issue_url(issue.get("number")),
                    "description": description[:200] + ("..." if len(description) > 200 else ""),
                    "bacon_estimate": 100,
                }
            )
        return json.dumps({"success": True, "data": results})
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to fetch good first issues: {e}")
        return json.dumps({"success": False, "error": str(e)})


# --- Original V1 Tools & Prompts ---


@mcp.tool()
async def submit_issue(
    url: str,
    title: str,
    description: str,
    severity: str | None = None,
    bug_type: str | None = None,
    steps_to_reproduce: str | None = None,
    labels: list[str] | None = None,
    assignee: str | None = None,
    confirmed: bool = False,
) -> str:
    """
    Submit a new issue to OWASP BLT.

    Args:
        url: The vulnerable URL being reported.
        title: Title of the bug/vulnerability.
        description: A detailed description of the bug or vulnerability.
        severity: Severity level of the issue (e.g., 'low', 'medium', 'high', 'critical').
        bug_type: The type of bug (e.g., 'XSS', 'SQLi').
        steps_to_reproduce: Step-by-step instructions to reproduce the issue.
        labels: Optional list of labels to apply to the issue (e.g., ['bug', 'security']).
        assignee: Optional username of the assignee for the issue.
        confirmed: Set to true to confirm execution of this write operation.
    """
    if not confirmed:
        logger.warning("Write operation 'submit_issue' blocked: confirmation required.")
        raise ValueError(
            "Write operation requires confirmation. Please set 'confirmed': true to proceed."
        )

    logger.info("Write operation 'submit_issue' confirmed. Proceeding to execution.")
    ai_metadata = generate_ai_metadata("submit_issue")

    logger.info(f"Submitting issue for url: {url}")

    full_description = f"Title: {title}\n\n{description}"
    payload = {
        "url": url,
        "title": title,
        "description": full_description,
    }
    if severity:
        payload["severity"] = severity.lower()
    if bug_type:
        payload["bug_type"] = bug_type
    if steps_to_reproduce:
        payload["steps_to_reproduce"] = steps_to_reproduce
    if labels:
        payload["labels"] = labels
    if assignee:
        payload["assignee"] = assignee

    headers = {
        "X-AI-Generated": "true",
        "X-AI-Source": "BLT-MCP",
        "X-AI-Timestamp": ai_metadata["timestamp"],
    }

    try:
        response = await server_base.http_client.post(
            "/bugs", json=payload, headers=headers
        )
        response.raise_for_status()
        try:
            issue_id = response.json().get("id", "Unknown")
        except json.JSONDecodeError:
            issue_id = response.text or "Unknown"

        return f"Successfully submitted issue for {url} (ID: {issue_id})"
    except httpx.HTTPStatusError as e:
        error_msg = f"API Error {e.response.status_code}: {e.response.text}"
        logger.error(error_msg)
        raise RuntimeError(f"Error executing tool submit_issue: {error_msg}") from e
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        logger.error(f"Failed to submit issue: {e}")
        raise RuntimeError(f"Failed to submit issue: {e}") from e



@mcp.tool()
async def summarize_issue_context(issue_id: str) -> str:
    """
    Generate a structured summary of an issue's context (title, description, comments, status).

    Args:
        issue_id: The ID of the issue to summarize.
    """
    return await summarize_issue_context_impl(issue_id, _fetch)


@mcp.tool()
async def triage_vulnerability(prompt: str) -> str:
    """
    Analyze a vulnerability description using Cloudflare Workers AI (Llama 3).

    Args:
        prompt: The full prompt string containing the issue details to analyze.
    """
    account_id = os.getenv("CF_ACCOUNT_ID")
    api_token = os.getenv("CF_API_TOKEN")

    if not account_id or not api_token:
        raise ValueError(
            "Missing Cloudflare credentials.\n\n"
            "Please add `CF_ACCOUNT_ID` and `CF_API_TOKEN` to your `BLT-MCP/.env` file "
            "to enable AI Triage using Cloudflare Workers AI."
        )

    system_msg = (
        "You are an expert security analyst assisting with OWASP BLT triage.\n"
        "1. Identify the vulnerability class (e.g. Injection, XSS, BAC).\n"
        "2. Assess the severity (Critical, High, Medium, Low).\n"
        "3. Recommend immediate mitigation steps.\n\n"
        "Please format your response clearly, starting with a Severity Suggestion, "
        "followed by your detailed Recommendation."
    )

    model = os.getenv("CF_MODEL") or "@cf/meta/llama-3.1-8b-instruct-fast"
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 1024,
    }

    logger.info("Sending prompt to Cloudflare Workers AI")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, headers=headers, json=payload, timeout=30.0
            )
            if response.status_code != 200:
                logger.error(f"Cloudflare AI Error: {response.text}")
                raise RuntimeError(
                    f"Cloudflare API returned status {response.status_code}"
                )

            result = response.json()
            if result.get("success"):
                response_text = result["result"]["response"]
                trimmed = response_text.strip()
                if not any(
                    trimmed.endswith(ext) for ext in (".", "!", "?", "```", "**", "*")
                ):
                    raise RuntimeError(
                        "Cloudflare AI response was truncated (incomplete output)."
                    )
                return response_text
            else:
                raise RuntimeError(
                    f"Cloudflare AI returned an error: {result.get('errors')}"
                )
    except Exception as e:
        if isinstance(e, (ValueError, RuntimeError)):
            raise
        logger.error(f"Exception calling CF AI: {e!s}")
        raise RuntimeError(f"Failed to call Cloudflare AI: {e!s}") from e


@mcp.tool()
async def draft_vision_issue(
    image_path: str,
    context: str | None = None,
) -> str:
    """Analyze a screenshot and draft a vulnerability issue report.

    Args:
        image_path: Absolute path to the screenshot image on the local system.
        context: Optional user-provided context or hints about the screenshot.
    """
    resolved_path = _validate_image_path(image_path)

    account_id = os.getenv("CF_ACCOUNT_ID")
    api_token = os.getenv("CF_API_TOKEN")

    if not account_id or not api_token:
        raise ValueError(
            "Missing Cloudflare credentials (CF_ACCOUNT_ID and CF_API_TOKEN in .env)."
        )

    logger.info(
        "Drafting issue from image %s; context_supplied=%s",
        os.path.basename(str(resolved_path)),
        bool(context and context.strip()),
    )

    try:
        image_bytes = await anyio.to_thread.run_sync(resolved_path.read_bytes)
    except Exception as e:
        raise RuntimeError(f"Failed to read image file: {e!s}") from e

    image_array = list(image_bytes)

    prompt = build_vision_prompt(context)

    model = (
        os.getenv("CF_VISION_MODEL")
        or "@cf/meta/llama-3.2-11b-vision-instruct"
    )
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    payload = {"prompt": prompt, "image": image_array}

    analysis_text = ""
    try:
        logger.info("Calling Cloudflare Vision AI...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, headers=headers, json=payload, timeout=60.0
            )
            if response.status_code != 200:
                logger.error(f"Cloudflare AI Error: {response.text}")
                raise RuntimeError(
                    f"Cloudflare API returned status {response.status_code}"
                )

            result = response.json()
            if result.get("success"):
                result_body = result.get("result")
                if not isinstance(result_body, dict):
                    result_body = {}
                analysis_text = result_body.get(
                    "description", result_body.get("response")
                )
            else:
                raise RuntimeError(
                    f"Cloudflare AI returned an error: {result.get('errors')}"
                )
    except Exception as e:
        if isinstance(e, (ValueError, RuntimeError)):
            raise
        logger.error(f"Exception calling CF Vision AI: {e!s}")
        raise RuntimeError(f"Failed to call Cloudflare Vision AI: {e!s}") from e

    try:
        return parse_vision_response(analysis_text)
    except ValueError as e:
        logger.error("Unusable Vision AI response: %s", e)
        raise RuntimeError(
            "Vision AI returned a response that could not be parsed into a title and "
            "description. Please try again."
        ) from e


def main(transport: str = "stdio", host: str = "127.0.0.1", port: int = 8080) -> None:
    """Entry point for the BLT-MCP server."""
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Could not set WindowsSelectorEventLoopPolicy: {e}")

    try:
        logger.info(
            f"Starting BLT-MCP server (transport={transport}, bind={host}:{port})..."
        )
        mcp.settings.host = host
        mcp.settings.port = port

        # Security check: remote transport must have BLT_MCP_TOKEN configured
        if transport != "stdio" and not os.getenv("BLT_MCP_TOKEN"):
            msg = (
                "\n"
                "========================================================================\n"
                "⚠️  SECURITY WARNING: Remote transport is enabled, but BLT_MCP_TOKEN    \n"
                "   environment variable is not set. The server will run WITHOUT        \n"
                "   authentication! Secure your server by setting BLT_MCP_TOKEN.         \n"
                "========================================================================\n"
            )
            print(msg, file=sys.stderr)
            logger.warning(msg.strip())

        # Monkeypatch the Starlette apps to inject token-based auth middleware if configured
        _apply_token_auth_middleware()

        if transport == "stdio":
            sys.stdin = StdinWrapper(
                sys.stdin, InterceptingStdinBuffer(sys.stdin.buffer)
            )
        mcp.run(transport=transport)
    except (KeyboardInterrupt, RuntimeError) as e:
        if isinstance(e, RuntimeError) and "Event loop is closed" not in str(e):
            raise
        logger.info("Server stopped.")
        return


def _apply_token_auth_middleware() -> None:
    class MCPTokenAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if request.method == "OPTIONS":
                return await call_next(request)

            expected_token = os.getenv("BLT_MCP_TOKEN")
            if not expected_token:
                return await call_next(request)

            auth_header = request.headers.get("Authorization")
            token = (
                auth_header[7:]
                if auth_header and auth_header.startswith("Bearer ")
                else None
            )

            # Fallback to query parameter token (required for browser EventSource SSE handshakes)
            if not token:
                token = request.query_params.get("token")

            if not token or not hmac.compare_digest(token, expected_token):
                return JSONResponse(
                    {"error": "Unauthorized: Invalid or missing BLT_MCP_TOKEN"},
                    status_code=401,
                )

            return await call_next(request)

    # Wrap sse_app and streamable_http_app methods
    orig_sse_app = mcp.sse_app

    def wrapped_sse_app(mount_path=None):
        app = orig_sse_app(mount_path)
        app.add_middleware(MCPTokenAuthMiddleware)
        return app

    mcp.sse_app = wrapped_sse_app

    orig_http_app = mcp.streamable_http_app

    def wrapped_http_app():
        app = orig_http_app()
        app.add_middleware(MCPTokenAuthMiddleware)
        return app

    mcp.streamable_http_app = wrapped_http_app


if __name__ == "__main__":
    main()
