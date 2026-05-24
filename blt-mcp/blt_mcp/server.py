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
    assignee: Optional[str] = None
) -> str:
    """
    Submit a new issue to OWASP BLT.
    
    Args:
        title: The title of the issue.
        description: A detailed description of the bug or vulnerability.
        repo_id: The ID of the repository to submit to (e.g., 'BLT-MCP'). Use list_repos to find IDs.
        labels: Optional list of labels to apply to the issue (e.g., ['bug', 'security']).
        assignee: Optional username of the assignee for the issue.
    """
    logger.info(f"Submitting issue: {title} to repo: {repo_id or 'default'}")
    payload = {
        "title": title,
        "description": description,
    }
    if repo_id is not None:
        payload["repo_id"] = repo_id
    if labels is not None:
        payload["labels"] = labels
    if assignee is not None:
        payload["assignee"] = assignee

    try:
        response = await http_client.post("/bugs", json=payload)
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
async def add_comment(issue_id: str, comment_text: str) -> str:
    """
    Add a comment to an existing BLT issue.
    
    Args:
        issue_id: The ID of the issue to comment on.
        comment_text: The text of the comment.
    """
    logger.info(f"Adding comment to issue: {issue_id}")
    try:
        response = await http_client.post(f"/bugs/{issue_id}/comments", json={"content": comment_text})
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

class InterceptingStdinBuffer(io.BufferedIOBase):
    def __init__(self, original):
        self.original = original
        self.buffer = b""

    def readable(self):
        return True

    def writable(self):
        return False

    def seekable(self):
        return False

    @property
    def closed(self):
        return self.original.closed

    def read(self, size=-1):
        if not self.buffer:
            # Stdio transport runs line-by-line. Using readline() prevents blocking.
            chunk = self.original.readline()
            if not chunk:
                return b""
            
            self.buffer += chunk
            self._process_buffer()

        if size is not None and size > 0:
            res = self.buffer[:size]
            self.buffer = self.buffer[size:]
            return res
        else:
            res = self.buffer
            self.buffer = b""
            return res

    def read1(self, size=-1):
        return self.read(size)

    def readline(self, limit=-1):
        if b"\n" not in self.buffer:
            chunk = self.original.readline(limit)
            if chunk:
                self.buffer += chunk
                self._process_buffer()
        
        if b"\n" in self.buffer:
            idx = self.buffer.index(b"\n") + 1
            res = self.buffer[:idx]
            self.buffer = self.buffer[idx:]
            return res
        else:
            res = self.buffer
            self.buffer = b""
            return res

    def _process_buffer(self):
        lines = self.buffer.split(b"\n")
        processed_lines = []
        for line in lines[:-1]:
            decoded = line.decode("utf-8", errors="ignore").strip()
            if decoded:
                try:
                    data = json.loads(decoded)
                    if isinstance(data, dict) and data.get("method") == "resources/read":
                        params = data.get("params")
                        if isinstance(params, dict) and "uri" not in params:
                            req_id = data.get("id")
                            error_resp = {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {
                                    "code": -32602,
                                    "message": "Invalid params: missing 'uri' parameter in resources/read"
                                }
                            }
                            sys.stdout.write(json.dumps(error_resp) + "\n")
                            sys.stdout.flush()
                            
                            ping_req = {
                                "jsonrpc": "2.0",
                                "id": f"dummy_{req_id}",
                                "method": "ping"
                            }
                            processed_lines.append(json.dumps(ping_req).encode("utf-8"))
                            continue
                except json.JSONDecodeError:
                    # Non-JSON line; pass through unchanged
                    pass
                except Exception as e:
                    logger.exception("Unexpected error while intercepting stdin: %s", e)
            processed_lines.append(line)
        
        self.buffer = b"\n".join(processed_lines)
        if len(lines) > 1:
            self.buffer += b"\n" + lines[-1]

class StdinWrapper:
    def __init__(self, original_stdin, intercepted_buffer):
        self.original_stdin = original_stdin
        self.buffer = intercepted_buffer

    def __getattr__(self, name):
        return getattr(self.original_stdin, name)

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
