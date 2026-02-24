"""Main entry point for BLT-Leaf PR Readiness Checker - Cloudflare Worker"""

from js import Response, URL
from slack_notifier import notify_slack_exception, notify_slack_error

# Import all handlers
from handlers import (
    handle_add_pr,
    handle_list_prs,
    handle_list_repos,
    handle_refresh_pr,
    handle_batch_refresh_prs,
    handle_rate_limit,
    handle_status,
    handle_pr_updates_check,
    handle_get_pr,
    handle_github_webhook,
    handle_pr_timeline,
    handle_pr_review_analysis,
    handle_pr_readiness,
    handle_scheduled_refresh
)


async def on_fetch(request, env):
    """Main request handler"""
    slack_webhook = getattr(env, 'SLACK_ERROR_WEBHOOK', '')

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

    try:
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
        
        # API endpoints
        response = None
        
        if path == '/api/prs/updates' and request.method == 'GET':
            response = await handle_pr_updates_check(env)
        elif path == '/api/prs':
            if request.method == 'GET':
                repo = url.searchParams.get('repo')
                org = url.searchParams.get('org')
                page = url.searchParams.get('page')
                per_page_param = url.searchParams.get('per_page')
                sort_by = url.searchParams.get('sort_by')
                sort_dir = url.searchParams.get('sort_dir')
                
                # Parse and validate per_page parameter
                per_page = 30  # default
                if per_page_param:
                    try:
                        per_page = int(per_page_param)
                        # Validate per_page is in allowed range (10-1000)
                        if per_page < 10:
                            per_page = 10
                        elif per_page > 1000:
                            per_page = 1000
                    except (ValueError, TypeError):
                        per_page = 30
                
                response = await handle_list_prs(
                    env,
                    repo,
                    page if page else 1,
                    per_page,
                    sort_by,
                    sort_dir,
                    org
                )
            elif request.method == 'POST':
                response = await handle_add_pr(request, env)
        # Single PR endpoint - GET /api/prs/{id}
        # The '/' check ensures sub-paths like /api/prs/{id}/timeline are not intercepted here
        elif path.startswith('/api/prs/') and '/' not in path[len('/api/prs/'):] and request.method == 'GET':
            pr_id_str = path[len('/api/prs/'):]
            if pr_id_str.isdigit():
                response = await handle_get_pr(env, int(pr_id_str))
        elif path == '/api/repos' and request.method == 'GET':
            response = await handle_list_repos(env)
        elif path == '/api/refresh' and request.method == 'POST':
            response = await handle_refresh_pr(request, env)
        elif path == '/api/refresh-batch' and request.method == 'POST':
            response = await handle_batch_refresh_prs(request, env)
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
        # Test error endpoint — deliberately raises to verify Slack error reporting
        elif path == '/api/test-error' and request.method == 'POST':
            raise RuntimeError('Slack test error — this exception was triggered intentionally from /api/test-error')
        # Frontend client-error reporting endpoint
        elif path == '/api/client-error' and request.method == 'POST':
            try:
                body = (await request.json()).to_py()
            except Exception:
                body = {}
            error_type = str(body.get('error_type', 'FrontendError'))
            error_message = str(body.get('message', 'Unknown frontend error'))
            stack_trace = str(body.get('stack', '')) or None
            ctx = {k: str(v) for k, v in body.items()
                   if k not in ('error_type', 'message', 'stack')}
            ctx['source'] = 'frontend'
            try:
                await notify_slack_error(
                    slack_webhook,
                    error_type=error_type,
                    error_message=error_message,
                    context=ctx,
                    stack_trace=stack_trace,
                )
            except Exception as slack_err:
                print(f'Slack: failed to report frontend error: {slack_err}')
            response = Response.new(
                '{"ok": true}',
                {'status': 200, 'headers': {'Content-Type': 'application/json'}},
            )
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

    except Exception as exc:
        try:
            await notify_slack_exception(slack_webhook, exc, context={
                'path': path,
                'method': str(request.method),
            })
        except Exception as slack_err:
            print(f'Slack: failed to report exception: {slack_err}')
        return Response.new(
            '{"error": "Internal server error"}',
            {'status': 500, 'headers': {**cors_headers, 'Content-Type': 'application/json'}},
        )


async def on_scheduled(controller, env, ctx):
    """Cloudflare Cron Trigger handler – runs every hour.

    Refreshes all PR records in the database using the minimal-request
    GraphQL batch API so that essential information stays current without
    consuming unnecessary GitHub API quota.
    """
    slack_webhook = getattr(env, 'SLACK_ERROR_WEBHOOK', '')
    try:
        await handle_scheduled_refresh(env)
    except Exception as exc:
        try:
            await notify_slack_exception(slack_webhook, exc, context={
                'handler': 'on_scheduled',
            })
        except Exception as slack_err:
            print(f'Slack: failed to report scheduled exception: {slack_err}')
        raise
