"""Main entry point for BLT-Rewards (BACON) - Cloudflare Worker"""

import json
from js import Response, URL, fetch, Object


async def on_fetch(request, env):
    """Main request handler"""
    url = URL.new(request.url)
    path = url.pathname
    
    # CORS headers
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    }
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return Response.new('', {'headers': cors_headers})
    
    # Redirect root path to index.html
    # Static assets are served directly by Cloudflare's asset handling configured in wrangler.toml
    if path == '/':
        return Response.new('', {
            'status': 302,
            'headers': {
                **cors_headers,
                'Location': '/index.html'
            }
        })
    
    # Return the SOL wallet balance using Solana's public JSON-RPC API
    if path == '/api/sol-balance':
        return await handle_sol_balance(env, cors_headers)
    
    # All other routes (including /index.html and other static files) 
    # are handled by Cloudflare's static asset serving
    # Return None to let Cloudflare serve the static asset
    return None


async def handle_sol_balance(env, cors_headers):
    """Fetch and return the SOL wallet balance from the Solana public RPC."""
    wallet_address = getattr(env, 'SOLANA_WALLET_ADDRESS', None)
    
    response_headers = {**cors_headers, 'Content-Type': 'application/json'}
    
    if not wallet_address:
        return Response.new(
            json.dumps({'balance': None, 'error': 'SOLANA_WALLET_ADDRESS not configured'}),
            {'headers': response_headers}
        )
    
    try:
        rpc_payload = json.dumps({
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'getBalance',
            'params': [wallet_address]
        })
        
        rpc_response = await fetch(
            'https://api.mainnet-beta.solana.com',
            Object.fromEntries([
                ['method', 'POST'],
                ['headers', Object.fromEntries([
                    ['Content-Type', 'application/json'],
                ])],
                ['body', rpc_payload],
            ])
        )
        
        rpc_data = await rpc_response.json()
        # Check for an RPC-level error response
        if hasattr(rpc_data, 'error') and rpc_data.error:
            return Response.new(
                json.dumps({'balance': None, 'error': str(rpc_data.error)}),
                {'headers': response_headers}
            )
        # rpc_data.result.value is the balance in lamports
        lamports = rpc_data.result.value
        sol_balance = lamports / 1_000_000_000
        
        return Response.new(
            json.dumps({'balance': sol_balance, 'address': wallet_address}),
            {'headers': response_headers}
        )
    except Exception as exc:
        return Response.new(
            json.dumps({'balance': None, 'error': str(exc)}),
            {'headers': response_headers}
        )
