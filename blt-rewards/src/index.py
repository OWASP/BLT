"""Main entry point for BLT-Rewards (BACON) - Cloudflare Worker"""

import json
from js import Response, URL, fetch, Object

# BACON SPL token mint address on Solana mainnet
# Verify at: https://explorer.solana.com/address/mntjJdXMvLkALMnyYFsdvxUnFXjLzLPpiNQwQSC58BL
BACON_MINT_ADDRESS = "mntjJdXMvLkALMnyYFsdvxUnFXjLzLPpiNQwQSC58BL"

# Default public Solana RPC URL; override via SOLANA_RPC_URL environment variable
DEFAULT_SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

def build_response(body, status=200, headers=None):
    """Build a Response with options correctly converted to a JS object.

    Response.new() is a JS binding, and passing it a plain Python dict for
    options silently drops keys like `status` during the Python-to-JS
    conversion — the response always comes back 200. Wrapping the options
    with Object.fromEntries() (the pattern already used for fetch() calls
    in this file) makes the status and headers apply correctly.
    """
    options = [['status', status]]
    if headers:
        options.append(['headers', Object.fromEntries(list(headers.items()))])
    return Response.new(body, Object.fromEntries(options))


async def on_fetch(request, env):
    """Main request handler"""
    url = URL.new(request.url)
    path = url.pathname

    # CORS headers
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    }

    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return build_response('', 200, cors_headers)


    if path in ('/api/sol-balance', '/api/token-supply'):
        # API routes only accept GET
        if request.method != 'GET':
            return build_response(
                json.dumps({'error': 'Method Not Allowed'}),
                405,
                {
                    **cors_headers,
                    'Content-Type': 'application/json',
                    'Allow': 'GET, OPTIONS',
                    'Cache-Control': 'no-store',
                }
            )

        # Return the SOL wallet balance using Solana's public JSON-RPC API
        if path == '/api/sol-balance':
            return await handle_sol_balance(env, cors_headers)

        # Return the BACON token total supply using Solana's public JSON-RPC API
        return await handle_token_supply(env, cors_headers)

    # Path doesn't match a known API route, and Cloudflare's static asset
    # handling didn't serve it either (otherwise this code wouldn't run) —
    # so it's a genuinely unknown path. Return 404 instead of letting it
    # fall through as an unhandled error.
    return build_response(
        json.dumps({'error': 'Page Not Found'}),
        404,
        {
            **cors_headers,
            'Content-Type': 'application/json',
            'Cache-Control': 'no-store',
        }
    )


async def handle_sol_balance(env, cors_headers):
    """Fetch and return the SOL wallet balance from the Solana public RPC."""
    wallet_address = getattr(env, 'SOLANA_WALLET_ADDRESS', None)
    rpc_url = getattr(env, 'SOLANA_RPC_URL', None) or DEFAULT_SOLANA_RPC_URL

    success_headers = {
        **cors_headers,
        'Content-Type': 'application/json',
        'Cache-Control': 'public, max-age=30',
    }
    error_headers = {
        **cors_headers,
        'Content-Type': 'application/json',
        'Cache-Control': 'no-store',
    }

    if not wallet_address:
        return build_response(
            json.dumps({'balance': None, 'error': 'SOLANA_WALLET_ADDRESS not configured'}),
            500,
            error_headers
        )

    try:
        rpc_payload = json.dumps({
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'getBalance',
            'params': [wallet_address]
        })

        rpc_response = await fetch(
            rpc_url,
            Object.fromEntries([
                ['method', 'POST'],
                ['headers', Object.fromEntries([
                    ['Content-Type', 'application/json'],
                ])],
                ['body', rpc_payload],
            ])
        )

        if not rpc_response.ok:
            return build_response(
                json.dumps({'balance': None, 'error': 'Solana RPC error: HTTP {}'.format(rpc_response.status)}),
                502,
                error_headers
            )

        rpc_data = await rpc_response.json()
        # Check for an RPC-level error response
        rpc_error = getattr(rpc_data, 'error', None)
        if rpc_error:
            return build_response(
                json.dumps({'balance': None, 'error': str(rpc_error)}),
                502,
                error_headers
            )
        # rpc_data.result.value is the balance in lamports
        lamports = rpc_data.result.value
        sol_balance = lamports / 1_000_000_000

        return build_response(
            json.dumps({'balance': sol_balance, 'address': wallet_address}),
            200,
            success_headers
        )
    except Exception:
        return build_response(
            json.dumps({'balance': None, 'error': 'Internal error'}),
            500,
            error_headers
        )


async def handle_token_supply(env, cors_headers):
    """Fetch and return the BACON token total supply from the Solana public RPC."""
    rpc_url = getattr(env, 'SOLANA_RPC_URL', None) or DEFAULT_SOLANA_RPC_URL

    success_headers = {
        **cors_headers,
        'Content-Type': 'application/json',
        'Cache-Control': 'public, max-age=30',
    }
    error_headers = {
        **cors_headers,
        'Content-Type': 'application/json',
        'Cache-Control': 'no-store',
    }

    try:
        rpc_payload = json.dumps({
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'getTokenSupply',
            'params': [BACON_MINT_ADDRESS]
        })

        rpc_response = await fetch(
            rpc_url,
            Object.fromEntries([
                ['method', 'POST'],
                ['headers', Object.fromEntries([
                    ['Content-Type', 'application/json'],
                ])],
                ['body', rpc_payload],
            ])
        )

        if not rpc_response.ok:
            return build_response(
                json.dumps({'supply': None, 'error': 'Solana RPC error: HTTP {}'.format(rpc_response.status)}),
                502,
                error_headers
            )

        rpc_data = await rpc_response.json()
        # Check for an RPC-level error response
        rpc_error = getattr(rpc_data, 'error', None)
        if rpc_error:
            return build_response(
                json.dumps({'supply': None, 'error': str(rpc_error)}),
                502,
                error_headers
            )
        # rpc_data.result.value.uiAmountString is the exact human-readable total supply
        supply = rpc_data.result.value.uiAmountString

        return build_response(
            json.dumps({'supply': supply, 'mint': BACON_MINT_ADDRESS}),
            200,
            success_headers
        )
    except Exception:
        return build_response(
            json.dumps({'supply': None, 'error': 'Internal error'}),
            500,
            error_headers
        )
