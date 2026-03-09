"""Main entry point for BLT-Leaf PR Readiness Checker - Cloudflare Worker"""
import json
from js import Response, URL, Object
from pyodide.ffi import to_js
from slack_notifier import notify_slack_exception, notify_slack_error
import json
from cache import check_rate_limit_bucket,should_send_dedupe, slack_budget_allow
# Import all handlers
from handlers import (
    handle_add_pr,
    handle_list_prs,
    handle_list_repos,
    handle_list_authors,
    handle_refresh_pr,
    handle_batch_refresh_prs,
    handle_refresh_org,
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

def _get_client_ip(request):
    return (
        request.headers.get('cf-connecting-ip')
        or (request.headers.get('x-forwarded-for') or '').split(',')[0].strip()
        or request.headers.get('x-real-ip')
        or 'unknown'
    )

def json_response(data: dict, status: int, extra_headers: dict | None = None):
    headers = {'Content-Type': 'application/json'}
    if extra_headers:
        headers.update(extra_headers)

    # Convert to a real JS init object so status is respected
    init = to_js(
        {'status': status, 'headers': headers},
        dict_converter=Object.fromEntries
    )
    return Response.new(json.dumps(data), init)
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
                author = url.searchParams.get('author')
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
                    org,
                    author
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
        elif path == '/api/authors' and request.method == 'GET':
            response = await handle_list_authors(env)
        elif path == '/api/refresh' and request.method == 'POST':
            response = await handle_refresh_pr(request, env)
        elif path == '/api/refresh-batch' and request.method == 'POST':
            response = await handle_batch_refresh_prs(request, env)
        elif path == '/api/refresh-org' and request.method == 'POST':
            response = await handle_refresh_org(request, env)
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
        
        elif path == '/api/error-test' and request.method == 'POST':
            ip = _get_client_ip(request)

            # Rate limit (keep it strict; default 1/min/IP)
            limit = int(getattr(env, 'ERROR_TEST_RATE_LIMIT', 1) or 1)
            window = int(getattr(env, 'ERROR_TEST_RATE_WINDOW', 60) or 60)
            allowed, retry_after = check_rate_limit_bucket('error-test', ip, limit, window)
            if not allowed:
                response = json_response(
                    {'ok': False, 'reason': 'Rate limit exceeded'},
                    429,
                    extra_headers={'Retry-After': str(retry_after)}
                )
                for k, v in cors_headers.items():
                    response.headers.set(k, v)
                return response

            slack_webhook = (getattr(env, 'SLACK_ERROR_WEBHOOK', '') or '').strip()
            if not slack_webhook:
                response = json_response({'ok': False, 'reason': 'SLACK_ERROR_WEBHOOK not set'}, 500)
                for k, v in cors_headers.items():
                    response.headers.set(k, v)
                return response

            try:
                await notify_slack_error(
                    slack_webhook,
                    error_type='ErrorTest',
                    error_message='Slack error-test triggered',
                    context={'source': '/api/error-test', 'url': str(request.url), 'ip': ip},
                    stack_trace=None,
                )
                response = json_response({'ok': True, 'sent_to_slack': True}, 200)
            except Exception as e:
                print(f'Error-test Slack send failed: {type(e).__name__}: {e}')
                response = json_response({'ok': False, 'reason': 'Slack send failed (check worker logs)'}, 502)

            for k, v in cors_headers.items():
                response.headers.set(k, v)
            return response
        # Frontend client-error reporting endpoint
        elif path == '/api/client-error' and request.method == 'POST':
            ip = _get_client_ip(request)

            # Rate limit per IP (default 10/min)
            limit = int(getattr(env, 'CLIENT_ERROR_RATE_LIMIT', 5) or 5)
            window = int(getattr(env, 'CLIENT_ERROR_RATE_WINDOW', 60) or 60)
            allowed, retry_after = check_rate_limit_bucket('client-error', ip, limit, window)
            if not allowed:
                response = json_response(
                    {'error': 'Rate limit exceeded'},
                    429,
                    extra_headers={'Retry-After': str(retry_after)}
                )
                for k, v in cors_headers.items():
                    response.headers.set(k, v)
                return response

            # Payload cap (default 8KB)
            max_bytes = int(getattr(env, 'CLIENT_ERROR_MAX_BYTES', 8192) or 8192)
            try:
                content_len = int(request.headers.get('content-length') or '0')
            except Exception:
                content_len = 0
            if content_len and content_len > max_bytes:
                response = json_response({'error': 'Payload too large'}, 413)
                for k, v in cors_headers.items():
                    response.headers.set(k, v)
                return response

            # Parse JSON once (tolerate beacon text/plain too)
            body = {}
            try:
                body = (await request.json()).to_py()
            except Exception:
                try:
                    text = await request.text()
                    body = json.loads(text) if text else {}
                except Exception:
                    body = {}

            error_type = str(body.get('error_type', 'FrontendError'))[:80]
            error_message = str(body.get('message', 'Unknown frontend error'))[:300]
            stack_trace = (str(body.get('stack', ''))[:2000] or None)

            url_here = str(body.get('url', ''))[:200] or ''
            line = str(body.get('line', ''))[:20] or ''
            col = str(body.get('col', ''))[:20] or ''
            resource = str(body.get('resource', ''))[:200] or ''

            # Dedupe key: same error signature shouldn't spam Slack
            dedupe_ttl = int(getattr(env, 'CLIENT_ERROR_DEDUPE_TTL', 300) or 300)  # 5 min default
            signature = f"{error_type}|{error_message}|{url_here}|{line}|{col}|{resource}"
            should_slack = should_send_dedupe(signature, dedupe_ttl)

            # Global Slack cap (default 20/min total)
            slack_cap = int(getattr(env, 'SLACK_MAX_PER_MIN', 20) or 20)
            slack_allowed, slack_retry = slack_budget_allow(slack_cap, 60)

            ctx = {k: str(v)[:200] for k, v in body.items() if k not in ('error_type', 'message', 'stack')}
            ctx['source'] = 'frontend'
            ctx['ip'] = ip
            ctx['dedupe'] = '1' if should_slack else '0'

            slack_sent = False
            if should_slack and slack_allowed:
                try:
                    await notify_slack_error(
                        slack_webhook,
                        error_type=error_type,
                        error_message=error_message,
                        context=ctx,
                        stack_trace=stack_trace,
                    )
                    slack_sent = True
                except Exception as slack_err:
                    print(f'Slack: failed to report frontend error: {slack_err}')
            else:
                # Optional: log why we skipped Slack
                if not should_slack:
                    print("Slack: deduped client-error")
                elif not slack_allowed:
                    print(f"Slack: global cap reached, retry after {slack_retry}s")

            response = json_response({'ok': True, 'slack_sent': slack_sent, 'deduped': (not should_slack)}, 200)
            for k, v in cors_headers.items():
                response.headers.set(k, v)
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
