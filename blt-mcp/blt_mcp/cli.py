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
from blt_mcp.oauth import pkce_login
from blt_mcp.server import main
from blt_mcp.server_base import BLT_API_BASE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("blt-mcp.cli")


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """BLT-MCP Command Line Interface"""
    if ctx.invoked_subcommand is None:
        # Backward compatibility: run the server if no command is given
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


@auth.command("login-pkce")
@click.option("--client-id", default="blt-mcp-cli", help="OAuth client ID")
@click.option("--port", default=9876, type=int, help="Local callback port")
def login_pkce(client_id, port):
    """Log in using OAuth 2.0 PKCE (browser-based)."""
    asyncio.run(_async_pkce_login(client_id, port))


async def _async_pkce_login(client_id: str, port: int):
    authorize_url = f"{BLT_API_BASE}/oauth/authorize"
    token_url = f"{BLT_API_BASE}/oauth/token"
    try:
        token = await pkce_login(authorize_url, token_url, client_id, port)
        save_credentials(token, auth_type="oauth_pkce")
        click.echo("Successfully logged in via OAuth PKCE and saved credentials.")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            click.echo(
                "\nError: OAuth endpoints returned 404. "
                "The BLT API backend does not currently support OAuth 2.0 PKCE flow.\n"
                "Please run standard login instead:\n"
                "  blt-mcp auth login\n",
                err=True,
            )
        else:
            click.echo(
                f"OAuth Token request failed: HTTP {e.response.status_code} - {e.response.text}",
                err=True,
            )
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        click.echo(f"PKCE login failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="stdio",
    help="Transport protocol for the MCP server.",
)
@click.option("--host", default="127.0.0.1", help="Host to bind (SSE/HTTP only).")
@click.option("--port", default=8080, type=int, help="Port to bind (SSE/HTTP only).")
def run(transport, host, port):
    """Run the MCP server"""
    main(transport=transport, host=host, port=port)


if __name__ == "__main__":
    cli()
