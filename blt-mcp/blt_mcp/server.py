import asyncio
import logging
import sys
import os
import json
import io
from typing import Any, Dict, List, Optional
import httpx
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from blt_mcp.validation import StdinWrapper, InterceptingStdinBuffer
from blt_mcp.tools import generate_ai_metadata, summarize_issue_context_impl

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("blt-mcp")

# API Configuration
BLT_API_BASE = os.getenv("BLT_API_BASE", "https://api.owaspblt.org")
BLT_API_KEY = os.getenv("BLT_API_KEY")

if not BLT_API_KEY:
    logger.warning("BLT_API_KEY not found in environment. Some tools may fail.")

# Shared HTTPX client
http_client: Optional[httpx.AsyncClient] = None

@asynccontextmanager
async def server_lifespan(server: FastMCP):
    """Manage the lifecycle of the HTTP client."""
    global http_client
    http_client = httpx.AsyncClient(
        base_url=BLT_API_BASE,
        headers={"X-BLT-API-Key": BLT_API_KEY} if BLT_API_KEY else {},
        timeout=30.0,
        follow_redirects=True
    )
    try:
        yield
    finally:
        logger.info("Closing HTTP client...")
        if http_client:
            await http_client.aclose()

# Initialize FastMCP server
mcp = FastMCP(
    "blt-mcp",
    dependencies=["click", "mcp"],
    lifespan=server_lifespan
)

async def _fetch(path: str, context: Optional[str] = None) -> str:
    try:
        response = await http_client.get(path)
        response.raise_for_status()
        return response.text
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to fetch {context or path}: {e}")
        raise RuntimeError(f"Failed to fetch {context or path}: {e}") from e
    except httpx.RequestError as e:
        logger.error(f"Failed to fetch {context or path}: {e}")
        raise RuntimeError(f"Failed to fetch {context or path}: {e}") from e

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
    return await _fetch(f"/bugs?repo_id={repo_id}", context=f"issues for repo {repo_id}")

@mcp.resource("blt://issues/{issue_id}")
async def get_issue(issue_id: str) -> str:
    """Get details for a specific BLT issue."""
    logger.info(f"Fetching details for issue: {issue_id}")
    return await _fetch(f"/bugs/{issue_id}", context=f"issue {issue_id}")

@mcp.tool()
async def submit_issue(
    title: str,
    description: str,
    repo_id: Optional[str] = None,
    labels: Optional[List[str]] = None,
    assignee: Optional[str] = None,
    confirmed: bool = False
) -> str:
    """
    Submit a new issue to OWASP BLT.
    
    Args:
        title: The title of the issue.
        description: A detailed description of the bug or vulnerability.
        repo_id: The ID of the repository to submit to (e.g., 'BLT-MCP'). Use list_repos to find IDs.
        labels: Optional list of labels to apply to the issue (e.g., ['bug', 'security']).
        assignee: Optional username of the assignee for the issue.
        confirmed: Set to true to confirm execution of this write operation.
    """
    if not confirmed:
        logger.warning("Write operation 'submit_issue' blocked: confirmation required.")
        raise ValueError("Write operation requires confirmation. Please set 'confirmed': true to proceed.")
        
    logger.info("Write operation 'submit_issue' confirmed. Proceeding to execution.")
    ai_metadata = generate_ai_metadata("submit_issue")
    
    logger.info(f"Submitting issue: {title} to repo: {repo_id or 'default'}")
    payload = {
        "title": title,
        "description": description,
        "metadata": ai_metadata
    }
    if repo_id is not None:
        payload["repo_id"] = repo_id
    if labels is not None:
        payload["labels"] = labels
    if assignee is not None:
        payload["assignee"] = assignee

    headers = {
        "X-AI-Generated": "true",
        "X-AI-Source": "BLT-MCP",
        "X-AI-Timestamp": ai_metadata["timestamp"]
    }

    try:
        response = await http_client.post("/bugs", json=payload, headers=headers)
        response.raise_for_status()
        try:
            issue_id = response.json().get('id', 'Unknown')
        except json.JSONDecodeError:
            issue_id = response.text or "Unknown"
            
        return f"Successfully submitted issue: {title} (ID: {issue_id})"
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to submit issue: {e}")
        raise RuntimeError(f"Failed to submit issue: {e}") from e
    except httpx.RequestError as e:
        logger.error(f"Failed to submit issue: {e}")
        raise RuntimeError(f"Failed to submit issue: {e}") from e

@mcp.tool()
async def add_comment(
    issue_id: str,
    comment_text: str,
    confirmed: bool = False
) -> str:
    """
    Add a comment to an existing BLT issue.
    
    Args:
        issue_id: The ID of the issue to comment on.
        comment_text: The text of the comment.
        confirmed: Set to true to confirm execution of this write operation.
    """
    if not confirmed:
        logger.warning("Write operation 'add_comment' blocked: confirmation required.")
        raise ValueError("Write operation requires confirmation. Please set 'confirmed': true to proceed.")
        
    logger.info("Write operation 'add_comment' confirmed. Proceeding to execution.")
    ai_metadata = generate_ai_metadata("add_comment")
    
    logger.info(f"Adding comment to issue: {issue_id}")
    payload = {
        "content": comment_text,
        "metadata": ai_metadata
    }
    
    headers = {
        "X-AI-Generated": "true",
        "X-AI-Source": "BLT-MCP",
        "X-AI-Timestamp": ai_metadata["timestamp"]
    }
    
    try:
        response = await http_client.post(f"/bugs/{issue_id}/comments", json=payload, headers=headers)
        response.raise_for_status()
        return f"Successfully added comment to issue {issue_id}"
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to add comment: {e}")
        raise RuntimeError(f"Failed to add comment: {e}") from e
    except httpx.RequestError as e:
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

@mcp.prompt()
def triage_vulnerability(description: str) -> str:
    """Create a prompt for triaging a vulnerability."""
    return f"Please triage the following vulnerability: {description}. Assess severity and suggest next steps."

# Validation helper classes have been extracted to blt_mcp/validation.py

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
