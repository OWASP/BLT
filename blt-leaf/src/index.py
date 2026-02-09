from js import Response, fetch, Headers, URL
import json
import re
from datetime import datetime

def parse_pr_url(pr_url):
    """Parse GitHub PR URL to extract owner, repo, and PR number"""
    pattern = r'https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)'
    match = re.match(pattern, pr_url)
    if match:
        return {
            'owner': match.group(1),
            'repo': match.group(2),
            'pr_number': int(match.group(3))
        }
    return None

async def fetch_pr_data(owner, repo, pr_number):
    """Fetch PR data from GitHub API"""
    try:
        # Fetch PR details
        pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        pr_response = await fetch(pr_url)
        pr_data = await pr_response.json()
        
        # Fetch PR files
        files_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
        files_response = await fetch(files_url)
        files_data = await files_response.json()
        
        # Fetch PR reviews
        reviews_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        reviews_response = await fetch(reviews_url)
        reviews_data = await reviews_response.json()
        
        # Fetch check runs
        checks_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{pr_data['head']['sha']}/check-runs"
        checks_response = await fetch(checks_url)
        checks_data = await checks_response.json()
        
        # Process check runs
        checks_passed = 0
        checks_failed = 0
        checks_skipped = 0
        
        if 'check_runs' in checks_data:
            for check in checks_data['check_runs']:
                if check['conclusion'] == 'success':
                    checks_passed += 1
                elif check['conclusion'] in ['failure', 'timed_out', 'cancelled']:
                    checks_failed += 1
                elif check['conclusion'] in ['skipped', 'neutral']:
                    checks_skipped += 1
        
        # Determine review status
        review_status = 'none'
        if reviews_data:
            latest_reviews = {}
            for review in reviews_data:
                user = review['user']['login']
                latest_reviews[user] = review['state']
            
            if 'CHANGES_REQUESTED' in latest_reviews.values():
                review_status = 'changes_requested'
            elif 'APPROVED' in latest_reviews.values():
                review_status = 'approved'
            else:
                review_status = 'pending'
        
        return {
            'title': pr_data.get('title', ''),
            'state': pr_data.get('state', ''),
            'is_merged': 1 if pr_data.get('merged', False) else 0,
            'mergeable_state': pr_data.get('mergeable_state', ''),
            'files_changed': len(files_data) if isinstance(files_data, list) else 0,
            'author_login': pr_data['user']['login'],
            'author_avatar': pr_data['user']['avatar_url'],
            'checks_passed': checks_passed,
            'checks_failed': checks_failed,
            'checks_skipped': checks_skipped,
            'review_status': review_status,
            'last_updated_at': pr_data.get('updated_at', '')
        }
    except Exception as e:
        print(f"Error fetching PR data: {str(e)}")
        return None

async def handle_add_pr(request, env):
    """Handle adding a new PR"""
    try:
        data = await request.json()
        pr_url = data.get('pr_url')
        
        if not pr_url:
            return Response.new(json.dumps({'error': 'PR URL is required'}), 
                              status=400,
                              headers={'Content-Type': 'application/json'})
        
        # Parse PR URL
        parsed = parse_pr_url(pr_url)
        if not parsed:
            return Response.new(json.dumps({'error': 'Invalid GitHub PR URL'}), 
                              status=400,
                              headers={'Content-Type': 'application/json'})
        
        # Fetch PR data from GitHub
        pr_data = await fetch_pr_data(parsed['owner'], parsed['repo'], parsed['pr_number'])
        if not pr_data:
            return Response.new(json.dumps({'error': 'Failed to fetch PR data from GitHub'}), 
                              status=500,
                              headers={'Content-Type': 'application/json'})
        
        # Insert or update in database
        stmt = env.DB.prepare('''
            INSERT INTO prs (pr_url, repo_owner, repo_name, pr_number, title, state, 
                           is_merged, mergeable_state, files_changed, author_login, 
                           author_avatar, checks_passed, checks_failed, checks_skipped, 
                           review_status, last_updated_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(pr_url) DO UPDATE SET
                title = excluded.title,
                state = excluded.state,
                is_merged = excluded.is_merged,
                mergeable_state = excluded.mergeable_state,
                files_changed = excluded.files_changed,
                checks_passed = excluded.checks_passed,
                checks_failed = excluded.checks_failed,
                checks_skipped = excluded.checks_skipped,
                review_status = excluded.review_status,
                last_updated_at = excluded.last_updated_at,
                updated_at = CURRENT_TIMESTAMP
        ''').bind(
            pr_url,
            parsed['owner'],
            parsed['repo'],
            parsed['pr_number'],
            pr_data['title'],
            pr_data['state'],
            pr_data['is_merged'],
            pr_data['mergeable_state'],
            pr_data['files_changed'],
            pr_data['author_login'],
            pr_data['author_avatar'],
            pr_data['checks_passed'],
            pr_data['checks_failed'],
            pr_data['checks_skipped'],
            pr_data['review_status'],
            pr_data['last_updated_at']
        )
        
        await stmt.run()
        
        return Response.new(json.dumps({'success': True, 'data': pr_data}), 
                          headers={'Content-Type': 'application/json'})
    except Exception as e:
        return Response.new(json.dumps({'error': str(e)}), 
                          status=500,
                          headers={'Content-Type': 'application/json'})

async def handle_list_prs(env, repo_filter=None):
    """List all PRs, optionally filtered by repo"""
    try:
        if repo_filter:
            parts = repo_filter.split('/')
            if len(parts) == 2:
                stmt = env.DB.prepare('''
                    SELECT * FROM prs 
                    WHERE repo_owner = ? AND repo_name = ?
                    ORDER BY last_updated_at DESC
                ''').bind(parts[0], parts[1])
            else:
                stmt = env.DB.prepare('SELECT * FROM prs ORDER BY last_updated_at DESC')
        else:
            stmt = env.DB.prepare('SELECT * FROM prs ORDER BY last_updated_at DESC')
        
        result = await stmt.all()
        prs = result.results if hasattr(result, 'results') else []
        
        return Response.new(json.dumps({'prs': prs}), 
                          headers={'Content-Type': 'application/json'})
    except Exception as e:
        return Response.new(json.dumps({'error': str(e)}), 
                          status=500,
                          headers={'Content-Type': 'application/json'})

async def handle_list_repos(env):
    """List all unique repos"""
    try:
        stmt = env.DB.prepare('''
            SELECT DISTINCT repo_owner, repo_name, 
                   COUNT(*) as pr_count
            FROM prs 
            GROUP BY repo_owner, repo_name
            ORDER BY repo_owner, repo_name
        ''')
        
        result = await stmt.all()
        repos = result.results if hasattr(result, 'results') else []
        
        return Response.new(json.dumps({'repos': repos}), 
                          headers={'Content-Type': 'application/json'})
    except Exception as e:
        return Response.new(json.dumps({'error': str(e)}), 
                          status=500,
                          headers={'Content-Type': 'application/json'})

async def handle_refresh_pr(request, env):
    """Refresh a specific PR's data"""
    try:
        data = await request.json()
        pr_id = data.get('pr_id')
        
        if not pr_id:
            return Response.new(json.dumps({'error': 'PR ID is required'}), 
                              status=400,
                              headers={'Content-Type': 'application/json'})
        
        # Get PR URL from database
        stmt = env.DB.prepare('SELECT pr_url, repo_owner, repo_name, pr_number FROM prs WHERE id = ?').bind(pr_id)
        result = await stmt.first()
        
        if not result:
            return Response.new(json.dumps({'error': 'PR not found'}), 
                              status=404,
                              headers={'Content-Type': 'application/json'})
        
        # Fetch fresh data from GitHub
        pr_data = await fetch_pr_data(result['repo_owner'], result['repo_name'], result['pr_number'])
        if not pr_data:
            return Response.new(json.dumps({'error': 'Failed to fetch PR data from GitHub'}), 
                              status=500,
                              headers={'Content-Type': 'application/json'})
        
        # Update database
        stmt = env.DB.prepare('''
            UPDATE prs SET
                title = ?, state = ?, is_merged = ?, mergeable_state = ?,
                files_changed = ?, checks_passed = ?, checks_failed = ?,
                checks_skipped = ?, review_status = ?, last_updated_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''').bind(
            pr_data['title'],
            pr_data['state'],
            pr_data['is_merged'],
            pr_data['mergeable_state'],
            pr_data['files_changed'],
            pr_data['checks_passed'],
            pr_data['checks_failed'],
            pr_data['checks_skipped'],
            pr_data['review_status'],
            pr_data['last_updated_at'],
            pr_id
        )
        
        await stmt.run()
        
        return Response.new(json.dumps({'success': True, 'data': pr_data}), 
                          headers={'Content-Type': 'application/json'})
    except Exception as e:
        return Response.new(json.dumps({'error': str(e)}), 
                          status=500,
                          headers={'Content-Type': 'application/json'})

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
        return Response.new('', headers=cors_headers)
    
    # Serve HTML for root path  
    if path == '/' or path == '/index.html':
        # Use env.ASSETS to serve static files if available
        if hasattr(env, 'ASSETS'):
            return await env.ASSETS.fetch(request)
        else:
            # Fallback: return simple message
            return Response.new('Please configure assets in wrangler.toml', 
                              status=200,
                              headers={**cors_headers, 'Content-Type': 'text/html'})
    
    # API endpoints
    if path == '/api/prs' and request.method == 'GET':
        repo_filter = url.searchParams.get('repo')
        response = await handle_list_prs(env, repo_filter)
        for key, value in cors_headers.items():
            response.headers.set(key, value)
        return response
    
    if path == '/api/prs' and request.method == 'POST':
        response = await handle_add_pr(request, env)
        for key, value in cors_headers.items():
            response.headers.set(key, value)
        return response
    
    if path == '/api/repos' and request.method == 'GET':
        response = await handle_list_repos(env)
        for key, value in cors_headers.items():
            response.headers.set(key, value)
        return response
    
    if path == '/api/refresh' and request.method == 'POST':
        response = await handle_refresh_pr(request, env)
        for key, value in cors_headers.items():
            response.headers.set(key, value)
        return response
    
    # Try to serve from assets
    if hasattr(env, 'ASSETS'):
        return await env.ASSETS.fetch(request)
    
    # 404
    return Response.new('Not Found', status=404, headers=cors_headers)
