"""Main entry point for BLT-Leaf PR Readiness Checker - Cloudflare Worker"""

from js import Response, URL

# Import database initialization
from database import init_database_schema

# Import all handlers
from handlers import (
    handle_add_pr,
    handle_list_prs,
    handle_list_repos,
    handle_refresh_pr,
    handle_rate_limit,
    handle_status,
    handle_pr_updates_check,
    handle_github_webhook,
    handle_pr_timeline,
    handle_pr_review_analysis,
    handle_pr_readiness
)


async def on_fetch(request, env):
    """Main request handler"""
    url = URL.new(request.url)
    path = url.pathname
    
    # Strip /leaf prefix
    if path == '/leaf': 
        path = '/'
    elif path.startswith('/leaf/'): 
        path = path[5:]  # Remove '/leaf' (5 characters)
    
    # CORS headers
    # NOTE: '*' allows all origins for public access. In production, consider
    # restricting to specific domains by setting this to your domain(s).
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, x-github-token',
    }
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return Response.new('', {'headers': cors_headers})
    
    # Serve HTML for root path 
    if path == '/' or path == '/index.html':
        # Use env.ASSETS to serve static files if available
        if hasattr(env, 'ASSETS'): 
            return await env.ASSETS.fetch(request)
        # Fallback: return simple message
        return Response.new('Please configure assets in wrangler.toml', 
                          {'status': 200, 'headers': {**cors_headers, 'Content-Type': 'text/html'}})
    
    # Initialize database schema on first API request (idempotent, safe to call multiple times)
    if path.startswith('/api/'): await init_database_schema(env)
    
    # API endpoints
    response = None
    
    if path == '/api/prs/updates' and request.method == 'GET':
        response = await handle_pr_updates_check(env)
    elif path == '/api/prs':
        if request.method == 'GET':
            repo = url.searchParams.get('repo')
            page = url.searchParams.get('page')
            sort_by = url.searchParams.get('sort_by')
            sort_dir = url.searchParams.get('sort_dir')
            response = await handle_list_prs(
                env,
                repo,
                page if page else 1,
                30,
                sort_by,
                sort_dir
            )
        elif request.method == 'POST':
            response = await handle_add_pr(request, env)
    elif path == '/api/repos' and request.method == 'GET':
        response = await handle_list_repos(env)
    elif path == '/api/refresh' and request.method == 'POST':
        response = await handle_refresh_pr(request, env)
    elif path == '/api/rate-limit' and request.method == 'GET':
        response = await handle_rate_limit(env)
        for key, value in cors_headers.items():
            response.headers.set(key, value)
        return response 
    elif path == '/api/status' and request.method == 'GET':
        response = await handle_status(env)
    elif path == '/api/github/webhook' and request.method == 'POST':
        response = await handle_github_webhook(request, env)
        for key, value in cors_headers.items():
            response.headers.set(key, value)
        return response
    # Timeline endpoint - GET /api/prs/{id}/timeline
    elif path.startswith('/api/prs/') and path.endswith('/timeline') and request.method == 'GET':
        response = await handle_pr_timeline(request, env, path)
        for key, value in cors_headers.items():
            response.headers.set(key, value)
        return response
    # Review analysis endpoint - GET /api/prs/{id}/review-analysis
    elif path.startswith('/api/prs/') and path.endswith('/review-analysis') and request.method == 'GET':
        response = await handle_pr_review_analysis(request, env, path)
        for key, value in cors_headers.items():
            response.headers.set(key, value)
        return response
    # PR readiness endpoint - GET /api/prs/{id}/readiness
    elif path.startswith('/api/prs/') and path.endswith('/readiness') and request.method == 'GET':
        response = await handle_pr_readiness(request, env, path)
        for key, value in cors_headers.items():
            response.headers.set(key, value)
        return response
    
    # If no API route matched, try static assets or return 404
    if response is None:
        if hasattr(env, 'ASSETS'): return await env.ASSETS.fetch(request)
        return Response.new('Not Found', {'status': 404, 'headers': cors_headers})
    
    # Apply CORS to API responses
    for key, value in cors_headers.items():
        if response: response.headers.set(key, value)
    return response
