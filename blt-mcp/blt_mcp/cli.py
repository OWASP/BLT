"""
Command Line Interface (CLI) for the OWASP BLT Model Context Protocol (MCP) Server.

This module uses the `click` library to define the command-line commands for the BLT-MCP server.
It provides commands for user authentication and running the local server.

Key Commands:
- `cli`: Parent group command. If invoked without subcommands, it defaults to running the MCP server.
- `auth login`: Prompts for user credentials (email and password), connects to the BLT auth endpoints
  to retrieve a JWT token, warns and requests confirmation before generating a broad wildcard API key,
  exchanges the token for a long-lived persistent key, and saves it locally.
- `run`: Directly starts the FastMCP server, establishing the stdio communication channel.

Design Details:
- Supports asynchronous authentication flows using Python's `asyncio` and `httpx.AsyncClient`.
- Implements secure, long-lived API key provisioning on behalf of the user.
- Provides operation-specific error handling to distinguish between sign-in failures and API key generation failures.

Dependencies:
- `sys`, `click`, `asyncio`, `logging`, `httpx`
- Submodules: `blt_mcp.server`, `blt_mcp.auth`, `blt_mcp.server_base`
"""

import asyncio
import logging
import sys

import click
import httpx

from blt_mcp.auth import save_credentials
from blt_mcp.server_base import BLT_API_BASE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("blt-mcp.cli")


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """BLT-MCP Command Line Interface"""
    if ctx.invoked_subcommand is None:
        # Backward compatibility: run the server if no command is given
        from blt_mcp.server import main

        main()


@cli.group()
def auth():
    """Authentication commands"""


@auth.command()
@click.option("--email", prompt="Email", help="Your BLT email address")
@click.option(
    "--password", prompt="Password", hide_input=True, help="Your BLT password"
)
def login(email: str, password: str):
    """Log in to BLT and save API credentials locally."""
    asyncio.run(_async_login(email, password))


async def _async_login(email: str, password: str):
    click.echo(f"Logging in to {BLT_API_BASE}...")
    current_op = "sign-in"
    async with httpx.AsyncClient(
        base_url=BLT_API_BASE, follow_redirects=True
    ) as client:
        try:
            # 1. Sign in to get JWT
            res = await client.post(
                "/auth/signin", json={"identifier": email, "password": password}
            )
            res.raise_for_status()
            data = res.json()
            jwt_token = data.get("access_token") or data.get("token")

            if not jwt_token:
                click.echo("Error: Login successful but no token received.", err=True)
                sys.exit(1)

            # Wildcard API key warning and user confirmation
            click.echo(
                "\nWARNING: Generating an API key with wildcard scopes ['*'] is required by the BLT API.\n"
                "This key is long-lived and provides broad access to all features on your account.\n"
                "Currently, the BLT API does not support narrower, fine-grained scopes for the MCP server."
            )
            if not click.confirm(
                "Do you want to generate this wildcard API key?", default=False
            ):
                click.echo("Aborted API key generation.", err=True)
                sys.exit(1)

            click.echo("Generating long-lived API key...")
            current_op = "api-key"

            # 2. Generate persistent API key
            headers = {"Authorization": f"Bearer {jwt_token}"}
            # NOTE: Wildcard scope is used because the BLT API does not
            # currently expose a granular scope vocabulary. If the backend adds
            # fine-grained scopes, narrow this to only what the MCP tools require.
            key_res = await client.post(
                "/api/auth/api-keys",
                json={"name": "BLT-MCP CLI", "scopes": ["*"]},
                headers=headers,
            )

            # In case the route is just /auth/api-keys depending on API version
            if key_res.status_code == 404:
                key_res = await client.post(
                    "/auth/api-keys",
                    json={"name": "BLT-MCP CLI", "scopes": ["*"]},
                    headers=headers,
                )

            key_res.raise_for_status()
            key_data = key_res.json()

            # Extract raw api key
            api_key = key_data.get("data", {}).get("api_key")
            if not api_key:
                click.echo(
                    "Error: API key not generated. Check your account permissions.",
                    err=True,
                )
                sys.exit(1)

            # 3. Save to credentials
            save_credentials(api_key)
            click.echo("Successfully generated and saved API key.")

        except httpx.HTTPStatusError as e:
            if current_op == "sign-in":
                click.echo(
                    f"Sign-in failed: HTTP {e.response.status_code}. Check your credentials.",
                    err=True,
                )
            else:
                click.echo(
                    f"API-key generation failed: HTTP {e.response.status_code}. Check your account permissions.",
                    err=True,
                )
            sys.exit(1)
        except Exception as e:  # noqa: BLE001
            click.echo(f"An error occurred: {e}", err=True)
            sys.exit(1)


@cli.command()
def run():
    """Run the MCP server"""
    from blt_mcp.server import main

    main()


if __name__ == "__main__":
    cli()
