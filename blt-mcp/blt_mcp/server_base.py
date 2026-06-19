
import os
import sys
import logging
import httpx
from typing import Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables from .env file relative to this file's directory
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
else:
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
    try:
        from blt_mcp.auth import load_credentials
        BLT_API_KEY = load_credentials()
        if BLT_API_KEY:
            logger.info("Loaded BLT_API_KEY from local credentials file.")
    except ImportError:
        pass

if not BLT_API_KEY:
    # Use the public static API key by default for OWASP BLT
    BLT_API_KEY = "f5537412b459790f9fa1cc47b862b9c7016471957178dc9b161d59355b6fd051"
    logger.info("BLT_API_KEY not found in environment or credentials. Defaulting to public static API key.")



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
