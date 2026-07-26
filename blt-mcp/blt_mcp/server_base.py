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

import os


import sys
import logging
import httpx
from typing import Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

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
http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def server_lifespan(server: FastMCP):
    """Manage the lifecycle of the HTTP client."""
    global http_client
    http_client = httpx.AsyncClient(
        base_url=BLT_API_BASE,
        headers={"X-BLT-API-Key": BLT_API_KEY} if BLT_API_KEY else {},
        timeout=30.0,
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
