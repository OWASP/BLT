#!/usr/bin/env python3
"""
Setup environment variables from .env.production for Cloudflare Workers.

This script reads environment variables from a .env file and configures them
in the Cloudflare Worker using wrangler.

Usage:
    python scripts/setup-env.py                 # Uses .env.production
    python scripts/setup-env.py /path/to/.env   # Uses custom env file
"""

import subprocess
import sys
from pathlib import Path


# Colors for terminal output
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    RESET = "\033[0m"


# Sensitive secrets that should use `wrangler secret put`
SECRETS = {
    "SLACK_TOKEN",
    "SIGNING_SECRET",
    "SLACK_CLIENT_ID",
    "SLACK_CLIENT_SECRET",
    "SENTRY_DSN",
    # Non-sensitive but set via wrangler secret for consistency
    "ENVIRONMENT",
    "JOINS_CHANNEL_ID",
    "CONTRIBUTE_ID",
    "DEPLOYS_CHANNEL",
    "BASE_URL",
}

# Reserved variables that should NOT be set (managed in wrangler.toml)
RESERVED = {
    "VERSION",
}


def load_env_file(env_file: Path) -> dict:
    """Load environment variables from a .env file."""
    env_vars = {}

    if not env_file.exists():
        print(
            f"{Colors.RED}Error: Environment file not found: {env_file}{Colors.RESET}"
        )
        sys.exit(1)

    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Remove 'export ' prefix if present
            if line.startswith("export "):
                line = line[7:].strip()

            # Parse key=value
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            # Remove quotes from value
            if value:
                value = value.strip("\"'")

            if key and value:
                env_vars[key] = value

    return env_vars


def set_secret(key: str, value: str) -> bool:
    """Set a secret using wrangler secret put."""
    try:
        process = subprocess.run(
            ["wrangler", "secret", "put", key],
            input=value.encode(),
            capture_output=True,
            timeout=10,
        )
        return process.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def main():
    # Determine env file path
    if len(sys.argv) > 1:
        env_file = Path(sys.argv[1])
    else:
        env_file = Path(".env.production")

    print(f"{Colors.YELLOW}Reading environment from: {env_file}{Colors.RESET}")

    # Load environment variables
    env_vars = load_env_file(env_file)

    if not env_vars:
        print(
            f"{Colors.YELLOW}No environment variables found in {env_file}{Colors.RESET}"
        )
        return 1

    print(f"{Colors.GREEN}Found {len(env_vars)} variables{Colors.RESET}\n")

    secret_count = 0
    skipped = 0

    # Process all variables as secrets
    for key, value in sorted(env_vars.items()):
        if key in SECRETS:
            # Set as secret on Cloudflare
            sys.stdout.write(f"Setting secret {key}... ")
            sys.stdout.flush()

            if set_secret(key, value):
                print(f"{Colors.GREEN}✓{Colors.RESET}")
                secret_count += 1
            else:
                print(f"{Colors.RED}✗{Colors.RESET}")

        elif key not in RESERVED:
            # Unknown variable
            print(f"{Colors.YELLOW}⊘ Skipping unknown variable: {key}{Colors.RESET}")
            skipped += 1

    print()
    print(f"{Colors.GREEN}✓ Environment setup complete!{Colors.RESET}")
    print(f"  • {secret_count} secrets set on Cloudflare")
    if skipped:
        print(f"  • {skipped} variables skipped")

    print()
    print("Next steps:")
    print("  1. Verify secrets: wrangler secret list")
    print("  2. Deploy: wrangler deploy")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
