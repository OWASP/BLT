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
        if hasattr(os, 'O_NOFOLLOW'):
            flags |= getattr(os, 'O_NOFOLLOW')
            
        fd = os.open(creds_path, flags, 0o600)
        with open(fd, 'w', encoding='utf-8') as f:
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
        data = json.loads(creds_path.read_text(encoding='utf-8'))
        return data.get("BLT_API_KEY")
    except Exception as e:
        logger.warning(f"Failed to load credentials from {creds_path}: {e}")
        return None
