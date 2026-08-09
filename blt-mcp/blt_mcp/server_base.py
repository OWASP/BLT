"""
Base Configurations and Shared Initialization Logic for the FastMCP Server.

This module initializes base configurations for the MCP server, including environment loading, logging,
and network clients. It acts as the shared foundation for all server modules.

Key Responsibilities:
- **Environment variables loading**: Checks for a local `.env` file in the root workspace folder,
  and falls back to standard shell variables if none is found.
- **Log routing**: Installs standard logging pointing to standard error (`sys.stderr`) to prevent
  corrupting standard out (`sys.stdout`) which is used for the MCP stdio communication channel.
- **FastMCP server initialization**: Instantiates the global `mcp` server.
- **Lifespan/lifecycle manager**: Registers `server_lifespan()` context manager to initialize and clean up
  the asynchronous HTTPX client (`httpx.AsyncClient`) used for all upstream queries to the BLT REST backend.

Shared Functions:
- `_fetch(path: str, context: Optional[str] = None) -> str`: Generic async helper to perform HTTP GET requests to the BLT backend,
  using the correct authorization headers, and returning the raw string response.
"""

import json
import logging
import os
import sys
from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Test Mocking: Hooked internally by pytest / mcp-vcr to run test suites deterministically
if os.getenv("BLT_MOCK_HTTP") == "true":
    original_send = httpx.AsyncClient.send

    async def mock_send(self, request, *args, **kwargs):
        url_str = str(request.url)
        path = request.url.path
        method = request.method

        # Default mock responses
        status_code = 200
        content_dict = {}
        handled = False

        if "api.cloudflare.com" in url_str:
            handled = True
            content_dict = {
                "success": True,
                "result": {
                    "response": "**Severity Suggestion:**\nHigh\n\n**Vulnerability Class:** SQL Injection\n\n**Detailed Recommendation:**\n\n### Immediate Mitigation Steps:\n\n1. **Validate and Sanitize User Input:**\n   - Ensure that the login form inputs (e.g., username and password) are validated and sanitized to prevent any malicious SQL code from being injected.\n   - Use prepared statements or parameterized queries to separate the SQL code from user input.\n\n2. **Use Whitelisting:**\n   - Implement a whitelisting approach to only allow specific characters or patterns in the login form inputs.\n   - This can be achieved by using regular expressions to validate the input data.\n\n3. **Implement Input Validation:**\n   - Validate the length and format of the input data to prevent any potential SQL injection attacks.\n   - For example, you can check if the username is not empty and contains only alphanumeric characters.\n\n4. **Review and Update the Database Schema:**\n   - Review the database schema to ensure that it is not vulnerable to SQL injection attacks.\n   - Consider updating the schema to use stored procedures or views to further secure the database.\n\n5. **Implement a Web Application Firewall (WAF):**\n   - Consider implementing a WAF to detect and prevent SQL injection attacks in real"
                },
            }
        elif "gitlab.com" in url_str:
            handled = True
            content_dict = [
                {
                    "id": 1,
                    "title": "Good First Issue 1",
                    "references": {"full": "org/repo1"},
                    "web_url": "https://gitlab.com/org/repo1/-/issues/1",
                    "description": "This is a good first issue description.",
                }
            ]
        elif path in ("/v2/bugs", "/bugs"):
            if method == "GET":
                handled = True
                content_dict = {
                    "success": True,
                    "data": [
                        {
                            "id": 1,
                            "url": "https://example.com",
                            "description": "*Submitted by AI Agent via BLT-MCP*\n\nTesting",
                            "status": "open",
                            "verified": 0,
                            "score": None,
                            "views": 0,
                            "created": "2026-07-01 10:33:58",
                            "modified": "2026-07-01 10:33:58",
                            "is_hidden": 0,
                            "rewarded": 0,
                            "cve_id": None,
                            "cve_score": None,
                            "domain": None,
                            "domain_name": None,
                            "domain_url": None,
                        }
                    ],
                    "pagination": {
                        "page": 1,
                        "per_page": 20,
                        "count": 1,
                        "total": 1,
                        "total_pages": 1,
                    },
                }
            elif method == "POST":
                handled = True
                content_dict = {"success": True, "id": "Unknown"}
        elif path == "/repos":
            if method == "GET":
                handled = True
                content_dict = [
                    {"id": 1, "name": "repo1", "description": "repositories"}
                ]
        elif path == "/stats":
            if method == "GET":
                handled = True
                content_dict = {
                    "total_issues": 10,
                    "active_repos": 2,
                    "statistics": "OWASP BLT Stats",
                }
        elif path == "/bugs/123":
            if method == "GET":
                handled = True
                content_dict = {
                    "title": "SQL Injection in Login Form",
                    "status": "open",
                    "description": "Found a SQL injection vulnerability in the username field.",
                }
        elif path == "/bugs/123/comments":
            if method == "GET":
                handled = True
                content_dict = [
                    {
                        "content": "I confirmed this vulnerability.",
                        "author": "security_researcher",
                    },
                    {"content": "Working on a fix now.", "author": "developer_bob"},
                ]
            elif method == "POST":
                handled = True
                content_dict = {"success": True}
        elif path.startswith("/bugs/") and path.endswith("/comments"):
            if method == "POST":
                handled = True
                content_dict = {"success": True}

        if not handled:
            raise AssertionError(f"Unmatched mock request: {method} {url_str}")

        return httpx.Response(
            status_code=status_code,
            content=json.dumps(content_dict).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            request=request,
        )

    httpx.AsyncClient.send = mock_send

# Load environment variables from .env file relative to this file's directory
env_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
)
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("blt-mcp")

# API Configuration
BLT_API_BASE = os.getenv("BLT_API_BASE", "https://api.owaspblt.org")
BLT_API_KEY = os.getenv("BLT_API_KEY")

if not BLT_API_KEY:
    try:
        from blt_mcp.auth import load_credentials

        BLT_API_KEY = load_credentials()
        if BLT_API_KEY:
            logger.info("Loaded BLT_API_KEY from local credentials file.")
    except ImportError:
        pass

if not BLT_API_KEY:
    logger.info("BLT_API_KEY not found in environment or credentials.")


# Shared HTTPX client
http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def server_lifespan(server: FastMCP):
    """Manage the lifecycle of the HTTP client."""
    global http_client
    http_client = httpx.AsyncClient(
        base_url=BLT_API_BASE,
        headers={"X-BLT-API-Key": BLT_API_KEY} if BLT_API_KEY else {},
        timeout=httpx.Timeout(15.0, connect=2.0),
        follow_redirects=True,
    )
    try:
        yield
    finally:
        logger.info("Closing HTTP client...")
        if http_client:
            await http_client.aclose()


# Initialize FastMCP server
mcp = FastMCP("blt-mcp", dependencies=["click", "mcp"], lifespan=server_lifespan)


async def _fetch(path: str, context: str | None = None) -> str:
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
