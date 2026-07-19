import sys
import logging
import json
import httpx
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from blt_mcp import server_base
from blt_mcp.server_base import mcp, _fetch, logger

from blt_mcp.validation import StdinWrapper, InterceptingStdinBuffer
from blt_mcp.tools import generate_ai_metadata, summarize_issue_context_impl

# Import v2 modular resources and tools to register them on the mcp instance
import blt_mcp.v2_resources
import blt_mcp.v2_tools

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
    """Get the list of cross-project 'good first issues' from GitLab."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://gitlab.com/api/v4/groups/133215711/issues?labels=good%20first%20issue&state=opened&sort=desc&order_by=updated_at",
                headers={"User-Agent": "BLT-MCP"},
            )
            resp.raise_for_status()
            issues = resp.json()
            # Map them into a standard format
            results = []
            for issue in issues:
                results.append(
                    {
                        "id": issue.get("id"),
                        "title": issue.get("title"),
                        "repository": issue.get("references", {}).get(
                            "full", "unknown"
                        ),
                        "web_url": issue.get("web_url"),
                        "description": issue.get("description", "")[:200] + "...",
                        "bacon_estimate": 100,  # Add Bacon estimate
                    }
                )
            return json.dumps({"success": True, "data": results})
    except Exception as e:
        logger.error(f"Failed to fetch good first issues: {e}")
        return json.dumps({"success": False, "error": str(e)})


# --- Original V1 Tools & Prompts ---


@mcp.tool()
async def submit_issue(
    url: str,
    title: str,
    description: str,
    severity: Optional[str] = None,
    bug_type: Optional[str] = None,
    steps_to_reproduce: Optional[str] = None,
    labels: Optional[List[str]] = None,
    assignee: Optional[str] = None,
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
async def add_comment(issue_id: str, comment_text: str, confirmed: bool = False) -> str:
    """
    Add a comment to an existing BLT issue.

    Args:
        issue_id: The ID of the issue to comment on.
        comment_text: The text of the comment.
        confirmed: Set to true to confirm execution of this write operation.
    """
    if not confirmed:
        logger.warning("Write operation 'add_comment' blocked: confirmation required.")
        raise ValueError(
            "Write operation requires confirmation. Please set 'confirmed': true to proceed."
        )

    logger.info("Write operation 'add_comment' confirmed. Proceeding to execution.")
    ai_metadata = generate_ai_metadata("add_comment")

    logger.info(f"Adding comment to issue: {issue_id}")
    payload = {"content": comment_text, "metadata": ai_metadata}

    headers = {
        "X-AI-Generated": "true",
        "X-AI-Source": "BLT-MCP",
        "X-AI-Timestamp": ai_metadata["timestamp"],
    }

    try:
        response = await server_base.http_client.post(
            f"/bugs/{issue_id}/comments", json=payload, headers=headers
        )
        response.raise_for_status()
        return f"Successfully added comment to issue {issue_id}"
    except Exception as e:
        logger.error(f"Failed to add comment: {e}")
        raise RuntimeError(f"Failed to add comment: {e}") from e


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

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3-8b-instruct"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ]
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
                return result["result"]["response"]
            else:
                raise RuntimeError(
                    f"Cloudflare AI returned an error: {result.get('errors')}"
                )
    except Exception as e:
        if isinstance(e, (ValueError, RuntimeError)):
            raise
        logger.error(f"Exception calling CF AI: {str(e)}")
        raise RuntimeError(f"Failed to call Cloudflare AI: {str(e)}") from e


@mcp.tool()
async def draft_vision_issue(
    image_path: str, gitlab_project_id: Optional[str] = None
) -> str:
    """
    Draft a vulnerability report (title and description) from a screenshot using Cloudflare Vision AI.
    Optionally uploads the image to GitLab if GITLAB_API_TOKEN is set.

    Args:
        image_path: Absolute path to the screenshot image on the local system.
        gitlab_project_id: Optional GitLab project ID to upload the image to.
    """
    allowed_dir = Path.home() / ".blt-mcp" / "images"
    allowed_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    allowed_dir.chmod(0o700)

    try:
        resolved_path = Path(image_path).resolve()
        if not resolved_path.is_relative_to(allowed_dir):
            raise ValueError(
                f"Image path must be within the server-owned directory: {allowed_dir}"
            )
    except AttributeError:
        # Fallback for Python versions without is_relative_to
        try:
            resolved_path.relative_to(allowed_dir)
        except ValueError:
            raise ValueError(
                f"Image path must be within the server-owned directory: {allowed_dir}"
            )

    if not resolved_path.exists() or not resolved_path.is_file():
        raise ValueError(f"Image file not found at {image_path}")

    allowed_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    if resolved_path.suffix.lower() not in allowed_exts:
        raise ValueError("Invalid image type. Allowed: png, jpg, jpeg, gif, webp")

    if resolved_path.stat().st_size > 10 * 1024 * 1024:
        raise ValueError("Image file exceeds maximum size of 10MB")

    account_id = os.getenv("CF_ACCOUNT_ID")
    api_token = os.getenv("CF_API_TOKEN")

    if not account_id or not api_token:
        raise ValueError(
            "Missing Cloudflare credentials (CF_ACCOUNT_ID and CF_API_TOKEN in .env)."
        )

    logger.info(f"Drafting issue from image: {image_path}")

    try:
        with open(resolved_path, "rb") as f:
            image_bytes = f.read()
    except Exception as e:
        raise RuntimeError(f"Failed to read image file: {str(e)}") from e

    # Cloudflare expects the image as an array of integers
    image_array = list(image_bytes)

    prompt = (
        "Analyze this screenshot of a web application. Identify any bugs, errors, or security vulnerabilities "
        "shown. Provide a structured response with two sections:\n\n"
        "TITLE: (A brief, clear title for the issue)\n\n"
        "DESCRIPTION: (A detailed explanation of what is wrong and how to reproduce it if apparent)."
    )

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/llava-hf/llava-1.5-7b-hf"
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
                analysis_text = (
                    result["result"]["description"]
                    if "description" in result["result"]
                    else result.get("result", {}).get(
                        "response", str(result.get("result"))
                    )
                )
            else:
                raise RuntimeError(
                    f"Cloudflare AI returned an error: {result.get('errors')}"
                )
    except Exception as e:
        if isinstance(e, (ValueError, RuntimeError)):
            raise
        logger.error(f"Exception calling CF Vision AI: {str(e)}")
        raise RuntimeError(f"Failed to call Cloudflare Vision AI: {str(e)}") from e

    # Optional GitLab Upload phase
    image_markdown = ""
    gl_token = os.getenv("GITLAB_API_TOKEN")
    if gitlab_project_id and gl_token:
        gl_url = f"https://gitlab.com/api/v4/projects/{gitlab_project_id}/uploads"
        gl_headers = {"PRIVATE-TOKEN": gl_token}

        try:
            logger.info("Uploading image to GitLab...")
            filename = os.path.basename(image_path)
            files = {"file": (filename, image_bytes, "image/png")}
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    gl_url, headers=gl_headers, files=files, timeout=30.0
                )
                if res.status_code == 201:
                    upload_data = res.json()
                    image_markdown = upload_data.get("markdown", "")
                else:
                    logger.warning(f"GitLab upload failed: {res.text}")
                    image_markdown = f"\n> [!WARNING]\n> Failed to upload image to GitLab (Status {res.status_code})"
        except Exception as e:
            logger.warning(f"GitLab upload exception: {str(e)}")
            image_markdown = (
                f"\n> [!WARNING]\n> Failed to upload image to GitLab: {str(e)}"
            )

    final_output = analysis_text
    if image_markdown:
        final_output += f"\n\n### Attached Screenshot\n{image_markdown}"

    return final_output


def main() -> None:
    """Entry point for the BLT-MCP server."""
    try:
        logger.info("Starting BLT-MCP server...")
        sys.stdin = StdinWrapper(sys.stdin, InterceptingStdinBuffer(sys.stdin.buffer))
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
        return


if __name__ == "__main__":
    main()
