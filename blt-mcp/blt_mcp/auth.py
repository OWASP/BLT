"""
Authentication and Local API Key Credentials Manager for the OWASP BLT MCP Server.

This module is responsible for persisting, loading, and locating the long-lived API token
(BLT_API_KEY) used to sign request headers for communication with the OWASP BLT backend API.

Key Responsibilities:
- Resolving the system path to locate the local credentials file in the user's home folder (`~/.blt-mcp/credentials.json`).
- Safely saving generated API keys with restricted owner-only read/write privileges (0o600 file permissions).
- Loading the key from credentials file on server start or CLI configuration updates.

Key Functions:
- `get_credentials_path() -> Path`: Resolves the absolute platform-independent config directory and returns the path to `credentials.json`.
- `save_credentials(api_key: str) -> None`: Safely writes the API key into the credentials file as a JSON map, using secure file open flags.
- `load_credentials() -> Optional[str]`: Loads and returns the raw API key if it exists, logging warnings if errors occur.

Dependencies:
- `os`, `json`, `logging`, `pathlib.Path`, `typing.Optional`
"""

import os


import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("blt-mcp.auth")


def get_credentials_path() -> Path:
    """Get the path to the credentials file."""
    # Use ~/.blt-mcp/credentials.json
    home = Path.home()
    config_dir = home / ".blt-mcp"
    config_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    return config_dir / "credentials.json"


def save_credentials(api_key: str) -> None:
    """Save the API key to the credentials file."""
    creds_path = get_credentials_path()
    try:
        # Save securely with read/write only for owner
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= getattr(os, "O_NOFOLLOW")

        fd = os.open(creds_path, flags, 0o600)
        # Enforce permissions even if file already existed (Unix-like systems)
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        with open(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps({"BLT_API_KEY": api_key}))

        logger.info(f"Credentials saved to {creds_path}")
    except Exception as e:
        logger.error(f"Failed to save credentials: {e}")
        raise


def load_credentials() -> Optional[str]:
    """Load the API key from the credentials file."""
    creds_path = get_credentials_path()
    if not creds_path.exists():
        return None

    try:
        data = json.loads(creds_path.read_text(encoding="utf-8"))
        return data.get("BLT_API_KEY")
    except Exception as e:
        logger.warning(f"Failed to load credentials from {creds_path}: {e}")
        return None
