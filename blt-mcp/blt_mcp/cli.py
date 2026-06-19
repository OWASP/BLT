import sys
import click
import asyncio
import getpass
import logging
import httpx
from blt_mcp.server import mcp
from blt_mcp.auth import save_credentials, load_credentials
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
    pass

@auth.command()
@click.option('--email', prompt='Email', help='Your BLT email address')
@click.option('--password', prompt='Password', hide_input=True, help='Your BLT password')
def login(email: str, password: str):
    """Log in to BLT and save API credentials locally."""
    asyncio.run(_async_login(email, password))

async def _async_login(email: str, password: str):
    click.echo(f"Logging in to {BLT_API_BASE}...")
    async with httpx.AsyncClient(base_url=BLT_API_BASE, follow_redirects=True) as client:
        try:
            # 1. Sign in to get JWT
            res = await client.post("/auth/signin", json={"identifier": email, "password": password})
            res.raise_for_status()
            data = res.json()
            jwt_token = data.get("access_token") or data.get("token")
            
            if not jwt_token:
                click.echo("Error: Login successful but no token received.", err=True)
                sys.exit(1)
            
            click.echo("Login successful! Generating long-lived API key...")
            
            # 2. Generate persistent API key
            headers = {"Authorization": f"Bearer {jwt_token}"}
            key_res = await client.post(
                "/api/auth/api-keys", 
                json={"name": "BLT-MCP CLI", "scopes": ["*"]},
                headers=headers
            )
            
            # In case the route is just /auth/api-keys depending on API version
            if key_res.status_code == 404:
                key_res = await client.post(
                    "/auth/api-keys",
                    json={"name": "BLT-MCP CLI", "scopes": ["*"]},
                    headers=headers
                )
            
            key_res.raise_for_status()
            key_data = key_res.json()
            
            # Extract raw api key
            api_key = key_data.get("data", {}).get("api_key")
            if not api_key:
                click.echo(f"Error: API key not generated. Response: {key_data}", err=True)
                sys.exit(1)
                
            # 3. Save to credentials
            save_credentials(api_key)
            click.echo("Successfully generated and saved API key.")
            
        except httpx.HTTPStatusError as e:
            click.echo(f"Authentication failed: HTTP {e.response.status_code} - {e.response.text}", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"An error occurred: {e}", err=True)
            sys.exit(1)

@cli.command()
def run():
    """Run the MCP server"""
    from blt_mcp.server import main
    main()

if __name__ == "__main__":
    cli()
