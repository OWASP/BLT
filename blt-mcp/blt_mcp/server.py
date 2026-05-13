import asyncio
import logging
import sys
import os
from typing import Any, Dict, List, Optional
import httpx
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

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
BLT_API_BASE = os.getenv("BLT_API_BASE", "https://blt.owasp.org/api")
BLT_API_KEY = os.getenv("BLT_API_KEY")

if not BLT_API_KEY:
    logger.warning("BLT_API_KEY not found in environment. Some tools may fail.")

# Shared HTTPX client
http_client = httpx.AsyncClient(
    base_url=BLT_API_BASE,
    headers={"Authorization": f"Bearer {BLT_API_KEY}"} if BLT_API_KEY else {},
    timeout=30.0
)

@asynccontextmanager
async def server_lifespan(server: FastMCP):
    """Manage the lifecycle of the HTTP client."""
    try:
        yield
    finally:
        logger.info("Closing HTTP client...")
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
    return await _fetch("/issues", context="issues")

@mcp.resource("blt://repos/{repo_id}/issues")
async def list_repo_issues(repo_id: str) -> str:
    """Get the list of issues for a specific repository."""
    logger.info(f"Fetching issues for repository: {repo_id}")
    return await _fetch(f"/repos/{repo_id}/issues", context=f"issues for repo {repo_id}")

@mcp.resource("blt://issues/{issue_id}")
async def get_issue(issue_id: str) -> str:
    """Get details for a specific BLT issue."""
    logger.info(f"Fetching details for issue: {issue_id}")
    return await _fetch(f"/issues/{issue_id}", context=f"issue {issue_id}")

@mcp.tool()
async def submit_issue(title: str, description: str, repo_id: Optional[str] = None) -> str:
    """
    Submit a new issue to OWASP BLT.
    
    Args:
        title: The title of the issue.
        description: A detailed description of the bug or vulnerability.
        repo_id: The ID of the repository to submit to (e.g., 'BLT-MCP'). Use list_repos to find IDs.
    """
    logger.info(f"Submitting issue: {title} to repo: {repo_id or 'default'}")
    payload = {
        "title": title,
        "description": description,
        "repo_id": repo_id
    }
    try:
        response = await http_client.post("/issues", json=payload)
        response.raise_for_status()
        return f"Successfully submitted issue: {title} (ID: {response.json().get('id')})"
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to submit issue: {e}")
        raise RuntimeError(f"Failed to submit issue: {e}") from e
    except httpx.RequestError as e:
        logger.error(f"Failed to submit issue: {e}")
        raise RuntimeError(f"Failed to submit issue: {e}") from e

@mcp.tool()
async def add_comment(issue_id: str, content: str) -> str:
    """
    Add a comment to an existing BLT issue.
    
    Args:
        issue_id: The ID of the issue to comment on.
        content: The text of the comment.
    """
    logger.info(f"Adding comment to issue: {issue_id}")
    try:
        response = await http_client.post(f"/issues/{issue_id}/comments", json={"content": content})
        response.raise_for_status()
        return f"Successfully added comment to issue {issue_id}"
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to add comment: {e}")
        raise RuntimeError(f"Failed to add comment: {e}") from e
    except httpx.RequestError as e:
        logger.error(f"Failed to add comment: {e}")
        raise RuntimeError(f"Failed to add comment: {e}") from e

@mcp.prompt()
def triage_vulnerability(description: str) -> str:
    """Create a prompt for triaging a vulnerability."""
    return f"Please triage the following vulnerability: {description}. Assess severity and suggest next steps."

def main() -> None:
    """Entry point for the BLT-MCP server."""
    try:
        logger.info("Starting BLT-MCP server...")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
        sys.exit(0)

if __name__ == "__main__":
    main()
