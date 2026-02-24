"""API endpoint handlers for PR tracking"""

import json
import re
from datetime import datetime, timezone
from js import Response, Headers, Object
from pyodide.ffi import to_js

# Import from our modules
from utils import (
    parse_pr_url, parse_repo_url, parse_org_url, calculate_review_status,
    build_pr_timeline, analyze_review_progress, classify_review_health,
    calculate_pr_readiness
)
from cache import (
    check_rate_limit, get_readiness_cache, set_readiness_cache,
    invalidate_readiness_cache, invalidate_timeline_cache, get_rate_limit_cache,
    _READINESS_CACHE_TTL, _RATE_LIMIT_CACHE_TTL, _READINESS_RATE_LIMIT,
    _READINESS_RATE_WINDOW, _rate_limit_cache
)
from database import get_db, upsert_pr
from github_api import (
    fetch_pr_data, fetch_pr_timeline_data, fetch_paginated_data,
    verify_github_signature, fetch_multiple_prs_batch, fetch_org_repos
)

# SQL expression for computed field: issues_count
# Calculates total issues as sum of blockers and warnings from JSON columns
# Uses COALESCE to handle NULL values (returns 0 if column is NULL or invalid JSON)
ISSUES_COUNT_SQL_EXPR = '(COALESCE(json_array_length(blockers), 0) + COALESCE(json_array_length(warnings), 0))'


async def handle_add_pr(request, env):
    """
    Handle adding a new PR or importing all PRs from a repo.
    
    Security Hardening (Issue #45):
    - Malformed JSON error handling
    - Type validation for pr_url parameter
    - Proper error handling for parse_pr_url ValueError
    """
    try:
        # Handle malformed JSON gracefully
        try:
            data = (await request.json()).to_py()
        except Exception:
            return Response.new(
                json.dumps({'error': 'Malformed JSON payload'}),
                {'status': 400, 'headers': {'Content-Type': 'application/json'}}
            )
        
        pr_url = data.get('pr_url')
        add_all = data.get('add_all', False)
        # Capture token from header - fall back to env secret for GraphQL API
        user_token = request.headers.get('x-github-token') or getattr(env, 'GITHUB_TOKEN', None)
        
        # Type validation for pr_url
        if not pr_url or not isinstance(pr_url, str):
            return Response.new(
                json.dumps({'error': 'A valid GitHub PR URL is required'}),
                {'status': 400, 'headers': {'Content-Type': 'application/json'}}
            )
        
        db = get_db(env)
        
        # Auto-detect URL type: if it's an org or repo URL (not a PR URL),
        # automatically treat as bulk import regardless of checkbox state
        if not add_all:
            # Check if the URL is an org URL or a repo URL (not a PR URL)
            if parse_org_url(pr_url) or (parse_repo_url(pr_url) and '/pull/' not in pr_url):
                add_all = True
        
        if add_all:
            # Try parsing as a repo URL first (e.g. https://github.com/owner/repo)
            parsed = parse_repo_url(pr_url)
            if parsed:
                # Single repo import
                repos_to_import = [{'owner': parsed['owner'], 'name': parsed['repo']}]
                is_org_import = False
            else:
                # Parse org url
                org_parsed = parse_org_url(pr_url)
                if not org_parsed:
                    return Response.new(json.dumps({'error': 'Invalid GitHub Repository or Organization URL'}), 
                                      {'status': 400, 'headers': {'Content-Type': 'application/json'}})
                
                org_owner = org_parsed['owner']
                is_org_import = True
                
                # Fetch all repos for the org/user
                try:
                    org_repos = await fetch_org_repos(org_owner, token=user_token)
                except Exception as e:
                    error_msg = str(e)
                    if 'status=403' in error_msg:
                        return Response.new(json.dumps({'error': 'Rate Limit Exceeded'}), 
                                          {'status': 403, 'headers': {'Content-Type': 'application/json'}})
                    return Response.new(json.dumps({'error': f'Failed to fetch organization repos: {error_msg}'}), 
                                      {'status': 400, 'headers': {'Content-Type': 'application/json'}})
                
                if not org_repos:
                    return Response.new(json.dumps({'error': f'No public repositories found for {org_owner}'}), 
                                      {'status': 404, 'headers': {'Content-Type': 'application/json'}})
                
                repos_to_import = [{'owner': r['owner'], 'name': r['name']} for r in org_repos]
            
            # Prepare headers for paginated fetching
            headers_dict = {
                'User-Agent': 'PR-Tracker/1.0',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28'
            }
            if user_token:
                headers_dict['Authorization'] = f'Bearer {user_token}'
            
            headers = Headers.new(to_js(headers_dict, dict_converter=Object.fromEntries))
            
            # Fetch open PRs with a safety limit to prevent timeouts on very large repos
            # Maximum 1000 PRs per import to stay within Cloudflare Workers execution limits
            MAX_PRS_PER_IMPORT = 1000
            added_count = 0
            truncated = False
            repos_imported = 0
            ts = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            
            for repo_info in repos_to_import:
                owner = repo_info['owner']
                repo = repo_info['name']
                
                # Calculate remaining capacity
                remaining = MAX_PRS_PER_IMPORT - added_count
                if remaining <= 0:
                    truncated = True
                    break
                
                # Explicitly sort by created date descending to get most recent PRs first
                list_url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=open&sort=created&direction=desc&per_page=100"
                
                try:
                    result = await fetch_paginated_data(list_url, headers, max_items=remaining, return_metadata=True)
                    prs_list = result['items']
                    if result['truncated']:
                        truncated = True
                except Exception as e:
                    error_msg = str(e)
                    if 'status=403' in error_msg:
                        truncated = True
                        break  # Rate limited - stop importing
                    # Skip repos that fail
                    print(f"Skipping repo {owner}/{repo}: {error_msg}")
                    continue
                
                if not prs_list:
                    continue
                
                repos_imported += 1
                
                for item in prs_list:
                    # Safely access user fields - user can be null for deleted accounts
                    user = item.get('user') or {}
                    
                    pr_data = {
                        'title': item.get('title', ''), 
                        'state': 'open', 
                        'is_merged': 0,
                        'mergeable_state': 'unknown', 
                        'files_changed': 0,
                        'author_login': user.get('login', 'ghost'), 
                        'author_avatar': user.get('avatar_url', ''),
                        'repo_owner_avatar': item.get('base', {}).get('repo', {}).get('owner', {}).get('avatar_url', ''),
                        'checks_passed': 0, 
                        'checks_failed': 0, 
                        'checks_skipped': 0,
                        'review_status': 'pending', 
                        'last_updated_at': item.get('updated_at', ts),
                        'commits_count': 0,
                        'behind_by': 0,
                        'is_draft': 1 if item.get('draft') else 0,
                        'reviewers_json': '[]'
                    }

                    await upsert_pr(db, item['html_url'], owner, repo, item['number'], pr_data)
                    added_count += 1
            
            # Build response message
            if is_org_import:
                message = f'Successfully imported {added_count} PR{"s" if added_count != 1 else ""} from {repos_imported} repo{"s" if repos_imported != 1 else ""} in {org_owner}'
            else:
                message = f'Successfully imported {added_count} PR{"s" if added_count != 1 else ""}'
            if truncated:
                message += f' (limited to {MAX_PRS_PER_IMPORT} most recent open PRs)'
            
            response_data = {
                'success': True, 
                'message': message,
                'imported_count': added_count,
                'truncated': truncated
            }
            
            return Response.new(json.dumps(response_data), 
                              {'headers': {'Content-Type': 'application/json'}})

        else:
            # Add single pr
            # Catch ValueError from parse_pr_url
            try:
                parsed = parse_pr_url(pr_url)
            except ValueError as e:
                return Response.new(
                    json.dumps({'error': str(e)}),
                    {'status': 400, 'headers': {'Content-Type': 'application/json'}}
                )
            
            # Fetch PR data 
            pr_data = await fetch_pr_data(parsed['owner'], parsed['repo'], parsed['pr_number'], user_token)
            
            if not pr_data:
                # If null returned
                return Response.new(json.dumps({'error': 'Failed to fetch PR data (Rate Limit or Not Found)'}), 
                                  {'status': 403, 'headers': {'Content-Type': 'application/json'}})
            
            if pr_data['is_merged'] or pr_data['state'] == 'closed':
                return Response.new(json.dumps({'error': 'Cannot add merged/closed PRs'}), 
                                  {'status': 400, 'headers': {'Content-Type': 'application/json'}})
            
            await upsert_pr(db, pr_url, parsed['owner'], parsed['repo'], parsed['pr_number'], pr_data)
            
            # Auto-run readiness analysis for the newly added PR
            readiness_data = None
            try:
                pr_result = await db.prepare(
                    'SELECT * FROM prs WHERE pr_url = ?'
                ).bind(pr_url).first()
                if pr_result:
                    pr_row = pr_result.to_py()
                    readiness_data = await _run_readiness_analysis(env, pr_row, pr_row['id'], user_token)
            except Exception as analysis_err:
                print(f"Auto-analysis failed for PR {pr_url}: {type(analysis_err).__name__}: {str(analysis_err)}")
            
            # Include repo_owner, repo_name, pr_number, and pr_url in the response for frontend display
            response_data = {
                **pr_data,
                'repo_owner': parsed['owner'],
                'repo_name': parsed['repo'],
                'pr_number': parsed['pr_number'],
                'pr_url': pr_url
            }
            
            result_obj = {'success': True, 'data': response_data}
            if readiness_data:
                result_obj['readiness'] = readiness_data
            
            return Response.new(json.dumps(result_obj), 
                              {'headers': {'Content-Type': 'application/json'}})

    except Exception as e:
        # Generic error message to prevent information disclosure
        print(f"Internal error in handle_add_pr: {type(e).__name__}: {str(e)}")
        return Response.new(
            json.dumps({'error': 'Internal server error'}),
            {'status': 500, 'headers': {'Content-Type': 'application/json'}}
        )

async def handle_list_prs(env, repo_filter=None, page=1, per_page=30, sort_by=None, sort_dir=None, org_filter=None):
    """List PRs with pagination and sorting (default 30 per page)."""
    try:
        db = get_db(env)
        try:
            page = int(page)
            if page < 1:
                page = 1
        except Exception:
            page = 1

        offset = (page - 1) * per_page
        base_query = '''
            FROM prs
            WHERE is_merged = 0 AND state = 'open'
        '''

        params = []

        if repo_filter:
            # repo_filter (owner/name) takes precedence over org_filter when both are provided
            parts = repo_filter.split('/')
            if len(parts) == 2:
                base_query += ' AND repo_owner = ? AND repo_name = ?'
                params.extend([parts[0], parts[1]])
        elif org_filter:
            base_query += ' AND repo_owner = ?'
            params.append(org_filter)

        # Map frontend column names to database column names or SQL expressions
        # This allows the UI to use friendly names that map to actual DB columns
        column_mapping = {
            'ready': 'merge_ready',  # Boolean flag: ready to merge (0/1)
            'ready_score': 'overall_score',  # Numeric score: 0-100%
            'overall': 'overall_score',  # Alias for ready_score
            'ci_score': 'ci_score',  # CI score: maps directly to database column
            'review_score': 'review_score',  # Review score: maps directly to database column
            'response_score': 'response_rate',
            'feedback_score': 'responded_feedback',
            # Computed field: uses module-level SQL expression constant
            'issues_count': ISSUES_COUNT_SQL_EXPR,
            # All other columns map directly to database columns
        }
        
        def is_valid_column_name(col_name):
            """Validate column name to prevent SQL injection.
            
            Only allows alphanumeric characters and underscores.
            This prevents injection while allowing all legitimate column names.
            """
            return bool(re.match(r'^[a-zA-Z0-9_]+$', col_name))
        
        def get_sort_expression(col_name):
            """Get SQL expression for a sort column with validation.
            
            Args:
                col_name: Column name from the frontend
                
            Returns:
                tuple: (sql_expression, is_valid)
                - sql_expression: SQL expression to use in ORDER BY, or None if invalid
                - is_valid: Whether the column is valid for sorting
            """
            # Check if column has a mapping (could be an expression)
            if col_name in column_mapping:
                return (column_mapping[col_name], True)
            
            # For unmapped columns, validate the name and use it directly
            if is_valid_column_name(col_name):
                return (col_name, True)
            
            # Invalid column name - reject
            return (None, False)
        
        # Parse multiple sort columns and directions
        # sort_by can be comma-separated list: "ready_score,title"
        # sort_dir can be comma-separated list: "desc,asc"
        sort_clauses = []
        
        if sort_by:
            # Split sort columns and directions
            sort_columns = [col.strip() for col in sort_by.split(',')]
            sort_directions = [dir.strip() for dir in sort_dir.split(',')] if sort_dir else []
            
            # Process each sort column
            for i, col in enumerate(sort_columns):
                # Get and validate the SQL expression for this column
                sql_expr, is_valid = get_sort_expression(col)
                
                if is_valid:
                    # Get corresponding direction or default to DESC
                    direction = 'DESC'
                    if i < len(sort_directions) and sort_directions[i].upper() in ('ASC', 'DESC'):
                        direction = sort_directions[i].upper()
                    
                    # Add NULL handling and column sort
                    # NULL values should appear last regardless of sort direction
                    sort_clauses.append(f'{sql_expr} IS NOT NULL DESC, {sql_expr} {direction}')
                else:
                    # Log invalid column attempts for security monitoring
                    print(f"Security: Rejected invalid sort column: {col}")
        
        # If no valid sort columns, use default
        if not sort_clauses:
            sort_clauses.append('last_updated_at IS NOT NULL, last_updated_at DESC')
        
        # Build ORDER BY clause
        # Note: All columns are validated via is_valid_column_name(), so no SQL injection risk
        order_clause = 'ORDER BY ' + ', '.join(sort_clauses)

        # Total count first
        count_stmt = db.prepare(f'''
            SELECT COUNT(*) as total
            {base_query}
        ''').bind(*params)

        count_result = await count_stmt.first()
        total = count_result.to_py()['total'] if count_result else 0

        # Fetch paginated data with sorting
        data_stmt = db.prepare(f'''
            SELECT *
            {base_query}
            {order_clause}
            LIMIT ? OFFSET ?
        ''').bind(*params, per_page, offset)

        result = await data_stmt.all()
        prs = result.results.to_py() if hasattr(result, 'results') else []

        return Response.new(json.dumps({
            'prs': prs,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_items': total,
                'total_pages': (total + per_page - 1) // per_page,
                'has_next': page * per_page < total,
                'has_previous': page > 1
            }
        }), {'headers': {
            'Content-Type': 'application/json',
            'Cache-Control': 'public, max-age=60, stale-while-revalidate=300'
        }})

    except Exception as e:
        return Response.new(
            json.dumps({'error': f"{type(e).__name__}: {str(e)}"}),
            {'status': 500, 'headers': {'Content-Type': 'application/json'}}
        )

async def handle_list_repos(env):
    """List all unique repos with count of open PRs"""
    try:
        db = get_db(env)
        stmt = db.prepare('''
            SELECT DISTINCT repo_owner, repo_name, 
                   COUNT(*) as pr_count,
                   SUM(CASE WHEN readiness_computed_at IS NOT NULL THEN 1 ELSE 0 END) as analyzed_count,
                   MAX(repo_owner_avatar) as repo_owner_avatar
            FROM prs 
            WHERE is_merged = 0 AND state = 'open'
            GROUP BY repo_owner, repo_name
            ORDER BY pr_count DESC, repo_owner, repo_name
        ''')
        
        result = await stmt.all()
        # Convert JS Array to Python list
        repos = result.results.to_py() if hasattr(result, 'results') else []
        
        return Response.new(json.dumps({'repos': repos}), 
                          {'headers': {
                              'Content-Type': 'application/json',
                              'Cache-Control': 'public, max-age=60, stale-while-revalidate=300'
                          }})
    except Exception as e:
        return Response.new(json.dumps({'error': f"{type(e).__name__}: {str(e)}"}), 
                          {'status': 500, 'headers': {'Content-Type': 'application/json'}})

async def handle_refresh_pr(request, env):
    """Refresh a specific PR's data"""
    try:
        data = (await request.json()).to_py()
        pr_id = data.get('pr_id')
        raw_quick_refresh = data.get('quick_refresh', False)
        if isinstance(raw_quick_refresh, bool):
            quick_refresh = raw_quick_refresh
        elif isinstance(raw_quick_refresh, str):
            quick_refresh = raw_quick_refresh.strip().lower() in ('true', '1', 'yes', 'on')
        else:
            quick_refresh = bool(raw_quick_refresh)
        user_token = request.headers.get('x-github-token') or getattr(env, 'GITHUB_TOKEN', None)
        
        if not pr_id:
            return Response.new(json.dumps({'error': 'PR ID is required'}), 
                              {'status': 400, 'headers': {'Content-Type': 'application/json'}})
        
        # Get PR URL and ETag from database
        db = get_db(env)
        stmt = db.prepare('SELECT pr_url, repo_owner, repo_name, pr_number, etag FROM prs WHERE id = ?').bind(pr_id)
        result = await stmt.first()
        
        if not result:
            return Response.new(json.dumps({'error': 'PR not found'}), 
                              {'status': 404, 'headers': {'Content-Type': 'application/json'}})
        
        # Convert JsProxy to Python dict to make it subscriptable
        result = result.to_py()
            
        # Fetch fresh data from GitHub (with Token and ETag)
        pr_data = await fetch_pr_data(
            result['repo_owner'], 
            result['repo_name'], 
            result['pr_number'], 
            user_token, 
            result.get('etag')
        )
        
        # Fast-Path: If data is unchanged (304 Not Modified), skip analysis and database update
        if pr_data and pr_data.get('not_modified'):
            print(f"Fast-path: PR #{result['pr_number']} data unchanged, skipping analysis")
            
            # Fetch existing PR data from DB to return to frontend
            # We already have some of it in 'result', but let's get the full row for completeness
            full_stmt = db.prepare('SELECT * FROM prs WHERE id = ?').bind(pr_id)
            full_result = await full_stmt.first()
            response_data = full_result.to_py() if hasattr(full_result, 'to_py') else dict(full_result)
            
            return Response.new(json.dumps({
                'success': True,
                'data': response_data,
                'fast_path': True,
                'rate_limit': get_rate_limit_cache()
            }), {'headers': {'Content-Type': 'application/json'}})
        
        if not pr_data:
            return Response.new(json.dumps({'error': 'Failed to fetch PR data from GitHub'}), 
                              {'status': 403, 'headers': {'Content-Type': 'application/json'}})
        
        # Check if PR is now merged or closed - delete it from database
        if pr_data['is_merged'] or pr_data['state'] == 'closed':
            # Invalidate caches since PR state changed
            await invalidate_readiness_cache(env, pr_id)
            await invalidate_timeline_cache(env, result['repo_owner'], result['repo_name'], result['pr_number'])
            
            # Delete the PR from database
            delete_stmt = db.prepare('DELETE FROM prs WHERE id = ?').bind(pr_id)
            await delete_stmt.run()
            
            status_msg = 'merged' if pr_data['is_merged'] else 'closed'
            return Response.new(json.dumps({
                'success': True, 
                'removed': True,
                'message': f'PR has been {status_msg} and removed from tracking'
            }), {'headers': {'Content-Type': 'application/json'}})
        
        await upsert_pr(db, result['pr_url'], result['repo_owner'], result['repo_name'], result['pr_number'], pr_data)
        
        # For a full Analyze refresh, invalidate readiness so stale scores are cleared.
        # For a quick refresh, preserve existing readiness data so the UI stays intact.
        if not quick_refresh:
            await invalidate_readiness_cache(env, pr_id)
        await invalidate_timeline_cache(env, result['repo_owner'], result['repo_name'], result['pr_number'])
        
        # Fetch the full updated DB row so the frontend receives all fields
        # (including updated_at, created_at, readiness_computed_at, etc.)
        full_stmt = db.prepare('SELECT * FROM prs WHERE id = ?').bind(pr_id)
        full_result = await full_stmt.first()
        if full_result:
            response_data = full_result.to_py() if hasattr(full_result, 'to_py') else dict(full_result)
        else:
            # Fallback: the row was just upserted so this shouldn't happen, but be safe
            response_data = {
                **pr_data,
                'repo_owner': result['repo_owner'],
                'repo_name': result['repo_name'],
                'pr_number': result['pr_number'],
                'pr_url': result['pr_url']
            }

        return Response.new(json.dumps({
            'success': True,
            'data': response_data,
            'rate_limit': get_rate_limit_cache()
        }), {'headers': {'Content-Type': 'application/json'}})
        
    except Exception as e:
        return Response.new(json.dumps({'error': f"{type(e).__name__}: {str(e)}"}),
                          {'status': 500, 'headers': {'Content-Type': 'application/json'}})

async def handle_batch_refresh_prs(request, env):
    """
    Refresh multiple PRs efficiently using batch API calls.
    
    POST /api/refresh-batch
    Body: { "pr_ids": [1, 2, 3, ...] }
    
    Uses GraphQL to fetch multiple PRs in a single API call.
    """
    try:
        data = (await request.json()).to_py()
        pr_ids = data.get('pr_ids', [])
        user_token = request.headers.get('x-github-token') or getattr(env, 'GITHUB_TOKEN', None)
        
        if not pr_ids or not isinstance(pr_ids, list):
            return Response.new(json.dumps({'error': 'pr_ids array is required'}), 
                              {'status': 400, 'headers': {'Content-Type': 'application/json'}})
        
        if len(pr_ids) > 100:
            return Response.new(json.dumps({'error': 'Maximum 100 PRs can be refreshed at once'}), 
                              {'status': 400, 'headers': {'Content-Type': 'application/json'}})
        
        # Get PR details from database
        db = get_db(env)
        prs_to_fetch = []
        pr_lookup = {}  # Maps (owner, repo, pr_number) -> (pr_id, pr_url, etag)
        
        for pr_id in pr_ids:
            stmt = db.prepare('SELECT pr_url, repo_owner, repo_name, pr_number, etag FROM prs WHERE id = ?').bind(pr_id)
            result = await stmt.first()
            
            if not result:
                print(f"PR ID {pr_id} not found, skipping")
                continue
            
            result = result.to_py()
            owner = result['repo_owner']
            repo = result['repo_name']
            pr_number = result['pr_number']
            pr_url = result['pr_url']
            etag = result.get('etag')
            
            prs_to_fetch.append((owner, repo, pr_number))
            pr_lookup[(owner, repo, pr_number)] = (pr_id, pr_url, etag)
        
        if not prs_to_fetch:
            return Response.new(json.dumps({'error': 'No valid PRs found'}), 
                              {'status': 404, 'headers': {'Content-Type': 'application/json'}})
        
        # Batch fetch PR data from GitHub
        print(f"Batch refreshing {len(prs_to_fetch)} PRs")
        batch_results = await fetch_multiple_prs_batch(prs_to_fetch, user_token)
        
        # Update database and collect results
        updated_prs = []
        removed_prs = []
        errors = []
        
        for (owner, repo, pr_number), pr_data in batch_results.items():
            pr_id, pr_url, etag = pr_lookup[(owner, repo, pr_number)]
            
            if not pr_data:
                errors.append({'pr_id': pr_id, 'pr_number': pr_number, 'error': 'Failed to fetch'})
                continue
            
            # Check if PR is now merged or closed - remove it
            # Note: GraphQL returns state in lowercase (e.g., 'closed', 'open')
            if pr_data['is_merged'] or pr_data['state'] == 'closed':
                await invalidate_readiness_cache(env, pr_id)
                await invalidate_timeline_cache(env, owner, repo, pr_number)
                
                delete_stmt = db.prepare('DELETE FROM prs WHERE id = ?').bind(pr_id)
                await delete_stmt.run()
                
                status_msg = 'merged' if pr_data['is_merged'] else 'closed'
                removed_prs.append({'pr_id': pr_id, 'pr_number': pr_number, 'status': status_msg})
                continue
            
            # Update PR data
            try:
                await upsert_pr(db, pr_url, owner, repo, pr_number, pr_data)
                await invalidate_readiness_cache(env, pr_id)
                await invalidate_timeline_cache(env, owner, repo, pr_number)
                updated_prs.append({'pr_id': pr_id, 'pr_number': pr_number})
            except Exception as update_error:
                print(f"Error updating PR #{pr_number} in {owner}/{repo}: {str(update_error)}")
                errors.append({'pr_id': pr_id, 'pr_number': pr_number, 'error': str(update_error)})
        
        return Response.new(json.dumps({
            'success': True,
            'updated': len(updated_prs),
            'removed': len(removed_prs),
            'errors': len(errors),
            'updated_prs': updated_prs,
            'removed_prs': removed_prs,
            'error_prs': errors,
            'rate_limit': get_rate_limit_cache()
        }), {'headers': {'Content-Type': 'application/json'}})
        
    except Exception as e:
        return Response.new(json.dumps({'error': f"{type(e).__name__}: {str(e)}"}),
                          {'status': 500, 'headers': {'Content-Type': 'application/json'}})
        
async def handle_rate_limit(env):
    """
    GET /api/rate-limit
    Returns the most recent GitHub API rate limit data captured locally.
    This avoids extra API calls and preserves your quota.
    """
    try:
        # Pull the latest state from the cache module
        rate_data = get_rate_limit_cache()
        token_configured = bool(getattr(env, 'GITHUB_TOKEN', None))
        
        # If no calls have been made yet, provide a friendly initial state
        if not rate_data or not rate_data.get('limit'):
            return Response.new(
                json.dumps({
                    'limit': 5000, 
                    'remaining': 5000, 
                    'reset': 0, 
                    'used': 0,
                    'status': 'waiting_for_first_request',
                    'token_configured': token_configured
                }), 
                {'headers': {'Content-Type': 'application/json'}}
            )
        
        return Response.new(
            json.dumps({**rate_data, 'token_configured': token_configured}), 
            {'headers': {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            }}
        )
    except Exception as e:
        print(f"Error in handle_rate_limit: {str(e)}")
        return Response.new(
            json.dumps({'error': 'Internal server error fetching rate status'}), 
            {'status': 500, 'headers': {'Content-Type': 'application/json'}}
        )

async def handle_status(env):
    """Check database status and return row counts"""
    try:
        db = get_db(env)
        # Query row counts for each table
        prs_result = await db.prepare('SELECT COUNT(*) as count FROM prs').first()
        timeline_result = await db.prepare('SELECT COUNT(*) as count FROM timeline_cache').first()

        def _row_to_dict(r):
            return r.to_py() if hasattr(r, 'to_py') else dict(r)

        prs_count = _row_to_dict(prs_result).get('count', 0) if prs_result else 0
        timeline_count = _row_to_dict(timeline_result).get('count', 0) if timeline_result else 0

        return Response.new(json.dumps({
            'database_configured': True,
            'environment': getattr(env, 'ENVIRONMENT', 'unknown'),
            'row_counts': {
                'prs': prs_count,
                'timeline_cache': timeline_count
            }
        }), {'headers': {'Content-Type': 'application/json'}})
    except Exception as e:
        # Database not configured
        return Response.new(json.dumps({
            'database_configured': False,
            'error': str(e),
            'environment': getattr(env, 'ENVIRONMENT', 'unknown'),
            'row_counts': {
                'prs': 0,
                'timeline_cache': 0
            }
        }), {'headers': {'Content-Type': 'application/json'}})

async def handle_pr_updates_check(env):
    """
    GET /api/prs/updates
    Lightweight endpoint to check for PR updates.
    Returns only PR IDs and their updated_at timestamps for change detection.
    
    This allows the frontend to poll efficiently without fetching full PR data.
    """
    try:
        db = get_db(env)
        
        # Fetch only IDs and timestamps - minimal data transfer
        stmt = db.prepare('SELECT id, updated_at FROM prs ORDER BY id')
        result = await stmt.all()
        
        if not result or not result.results:
            return Response.new(
                json.dumps({'updates': []}),
                {'headers': {'Content-Type': 'application/json'}}
            )
        
        # Convert to lightweight format
        updates = []
        for row in result.results:
            row_dict = row.to_py()
            updates.append({
                'id': row_dict.get('id'),
                'updated_at': row_dict.get('updated_at')
            })
        
        return Response.new(
            json.dumps({'updates': updates}),
            {'headers': {'Content-Type': 'application/json'}}
        )
    except Exception as e:
        return Response.new(
            json.dumps({'error': f"{type(e).__name__}: {str(e)}"}),
            {'status': 500, 'headers': {'Content-Type': 'application/json'}}
        )

async def handle_get_pr(env, pr_id):
    """
    GET /api/prs/{id}
    Fetch a single PR's stored data from the database.
    Used by the frontend periodic checker to update individual rows
    without reloading the entire PR list.
    """
    try:
        db = get_db(env)
        stmt = db.prepare('SELECT * FROM prs WHERE id = ? AND is_merged = 0 AND state = \'open\'').bind(pr_id)
        result = await stmt.first()

        if not result:
            return Response.new(
                json.dumps({'error': 'PR not found'}),
                {'status': 404, 'headers': {'Content-Type': 'application/json'}}
            )

        pr = result.to_py() if hasattr(result, 'to_py') else dict(result)

        return Response.new(
            json.dumps({'pr': pr}),
            {'headers': {'Content-Type': 'application/json'}}
        )
    except Exception as e:
        return Response.new(
            json.dumps({'error': f"{type(e).__name__}: {str(e)}"}),
            {'status': 500, 'headers': {'Content-Type': 'application/json'}}
        )


async def verify_github_signature(request, payload_body, secret):
    """
    Verify GitHub webhook signature.
    
    Args:
        request: The request object containing headers
        payload_body: Raw request body as bytes or string
        secret: Webhook secret configured in GitHub
        
    Returns:
        bool: True if signature is valid, False otherwise
    """
    if not secret:
        # If no secret is configured, skip verification (development mode)
        print("WARNING: Webhook secret not configured - skipping signature verification")
        return True
    
    signature_header = request.headers.get('x-hub-signature-256')
    if not signature_header:
        return False
    
    # GitHub sends signature as "sha256=<hash>"
    try:
        import hashlib
        import hmac
        
        # Ensure payload_body is bytes
        if isinstance(payload_body, str):
            payload_body = payload_body.encode('utf-8')
        
        # Calculate expected signature
        hash_object = hmac.new(secret.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
        expected_signature = "sha256=" + hash_object.hexdigest()
        
        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected_signature, signature_header)
    except Exception as e:
        print(f"Error verifying webhook signature: {e}")
        return False

async def handle_github_webhook(request, env):
    """
    POST /api/github/webhook
    Handle GitHub webhook events for PR state changes.
    
    Supported events:
    - pull_request: opened, closed, reopened, synchronize, edited
    - pull_request_review: submitted, edited, dismissed (updates PR data)
    - check_run: completed, requested_action (updates PR data)
    - check_suite: completed, requested (updates PR data)
    
    Security:
    - Verifies GitHub webhook signature using WEBHOOK_SECRET
    - Validates event types before processing
    
    When a PR is opened:
    - Automatically adds the PR to tracking
    - Fetches complete PR data from GitHub
    - Returns event data with PR ID for frontend
    
    When a PR is closed or merged:
    - Removes the PR from the database
    - Returns event data for frontend to animate removal
    
    When a PR is updated (synchronize, edited, reviews, checks):
    - Refreshes PR data in the database including behind_by and mergeable_state
    - Invalidates caches to ensure fresh analysis
    - Returns updated PR data for frontend
    """
    try:
        # Get webhook secret from environment
        webhook_secret = getattr(env, 'GITHUB_WEBHOOK_SECRET', None)
        
        # Get raw request body for signature verification
        raw_body = await request.text()
        
        # Verify webhook signature
        if not await verify_github_signature(request, raw_body, webhook_secret):
            return Response.new(
                json.dumps({'error': 'Invalid webhook signature'}),
                {'status': 401, 'headers': {'Content-Type': 'application/json'}}
            )
        
        # Parse webhook payload
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            return Response.new(
                json.dumps({'error': 'Invalid JSON payload'}),
                {'status': 400, 'headers': {'Content-Type': 'application/json'}}
            )
        
        # Get event type from header
        event_type = request.headers.get('x-github-event')
        
        if event_type == 'pull_request':
            action = payload.get('action')
            pr_data = payload.get('pull_request', {})
            repo_data = payload.get('repository', {})
            
            # Extract PR details
            pr_number = pr_data.get('number')
            repo_owner = repo_data.get('owner', {}).get('login')
            repo_name = repo_data.get('name')
            state = pr_data.get('state')
            merged = pr_data.get('merged', False)
            
            if not all([pr_number, repo_owner, repo_name]):
                return Response.new(
                    json.dumps({'error': 'Missing required PR data'}),
                    {'status': 400, 'headers': {'Content-Type': 'application/json'}}
                )
            
            # Find the PR in our database
            db = get_db(env)
            pr_url = f"https://github.com/{repo_owner}/{repo_name}/pull/{pr_number}"
            result = await db.prepare(
                'SELECT id FROM prs WHERE pr_url = ?'
            ).bind(pr_url).first()
            
            # Handle opened PRs - add to tracking automatically
            if action == 'opened':
                if result:
                    # PR already tracked, just return success
                    return Response.new(
                        json.dumps({
                            'success': True,
                            'event': 'pr_already_tracked',
                            'pr_id': result.to_py()['id'],
                            'pr_number': pr_number,
                            'message': f'PR #{pr_number} is already being tracked'
                        }),
                        {'headers': {'Content-Type': 'application/json'}}
                    )
                
                # Fetch fresh PR data and add to tracking
                webhook_token = getattr(env, 'GITHUB_TOKEN', None)
                fetched_pr_data = await fetch_pr_data(repo_owner, repo_name, pr_number, webhook_token)
                if fetched_pr_data:
                    await upsert_pr(db, pr_url, repo_owner, repo_name, pr_number, fetched_pr_data)
                    
                    # Get the newly created PR ID
                    new_result = await db.prepare(
                        'SELECT id FROM prs WHERE pr_url = ?'
                    ).bind(pr_url).first()
                    new_pr_id = new_result.to_py()['id'] if new_result else None
                    
                    return Response.new(
                        json.dumps({
                            'success': True,
                            'event': 'pr_added',
                            'pr_id': new_pr_id,
                            'pr_number': pr_number,
                            'data': fetched_pr_data,
                            'message': f'PR #{pr_number} has been added to tracking'
                        }),
                        {'headers': {'Content-Type': 'application/json'}}
                    )
                else:
                    return Response.new(
                        json.dumps({'error': 'Failed to fetch PR data from GitHub'}),
                        {'status': 500, 'headers': {'Content-Type': 'application/json'}}
                    )
            
            if not result:
                # PR not being tracked - ignore this webhook for other actions
                return Response.new(
                    json.dumps({
                        'success': True,
                        'message': 'PR not tracked, ignoring webhook'
                    }),
                    {'headers': {'Content-Type': 'application/json'}}
                )
            
            pr_id = result.to_py()['id']
            
            # Handle closed/merged PRs - remove from database
            if action == 'closed' or merged or state == 'closed':
                # Invalidate caches
                await invalidate_readiness_cache(env, pr_id)
                await invalidate_timeline_cache(env, repo_owner, repo_name, pr_number)
                
                # Delete the PR
                await db.prepare('DELETE FROM prs WHERE id = ?').bind(pr_id).run()
                
                status_msg = 'merged' if merged else 'closed'
                return Response.new(
                    json.dumps({
                        'success': True,
                        'event': 'pr_removed',
                        'pr_id': pr_id,
                        'pr_number': pr_number,
                        'status': status_msg,
                        'message': f'PR #{pr_number} has been {status_msg} and removed from tracking'
                    }),
                    {'headers': {'Content-Type': 'application/json'}}
                )
            
            # Handle reopened PRs - re-add to tracking if it was tracked before
            elif action == 'reopened':
                # Fetch fresh PR data
                webhook_token = getattr(env, 'GITHUB_TOKEN', None)
                fetched_pr_data = await fetch_pr_data(repo_owner, repo_name, pr_number, webhook_token)
                if fetched_pr_data:
                    await upsert_pr(db, pr_url, repo_owner, repo_name, pr_number, fetched_pr_data)
                    # Invalidate caches
                    await invalidate_readiness_cache(env, pr_id)
                    await invalidate_timeline_cache(env, repo_owner, repo_name, pr_number)
                    
                    return Response.new(
                        json.dumps({
                            'success': True,
                            'event': 'pr_reopened',
                            'pr_id': pr_id,
                            'pr_number': pr_number,
                            'data': fetched_pr_data,
                            'message': f'PR #{pr_number} has been reopened'
                        }),
                        {'headers': {'Content-Type': 'application/json'}}
                    )
            
            # Handle synchronized (new commits) or edited PRs - update data
            elif action in ['synchronize', 'edited']:
                # Fetch fresh PR data
                webhook_token = getattr(env, 'GITHUB_TOKEN', None)
                fetched_pr_data = await fetch_pr_data(repo_owner, repo_name, pr_number, webhook_token)
                if fetched_pr_data:
                    await upsert_pr(db, pr_url, repo_owner, repo_name, pr_number, fetched_pr_data)
                    # Invalidate caches to force fresh analysis
                    await invalidate_readiness_cache(env, pr_id)
                    await invalidate_timeline_cache(env, repo_owner, repo_name, pr_number)
                    
                    return Response.new(
                        json.dumps({
                            'success': True,
                            'event': 'pr_updated',
                            'pr_id': pr_id,
                            'pr_number': pr_number,
                            'data': fetched_pr_data,
                            'message': f'PR #{pr_number} has been updated'
                        }),
                        {'headers': {'Content-Type': 'application/json'}}
                    )
        
        # Handle other event types - update PR data to refresh behind_by and mergeable_state
        elif event_type in ['pull_request_review', 'check_run', 'check_suite']:
            # Extract PR information from the payload based on event type
            prs_to_update = []  # List of (pr_number, repo_owner, repo_name) tuples
            
            if event_type == 'pull_request_review':
                # pull_request_review events have PR data directly
                pr_data = payload.get('pull_request', {})
                repo_data = payload.get('repository', {})
                pr_number = pr_data.get('number')
                repo_owner = repo_data.get('owner', {}).get('login')
                repo_name = repo_data.get('name')
                if all([pr_number, repo_owner, repo_name]):
                    prs_to_update.append((pr_number, repo_owner, repo_name))
            elif event_type in ['check_run', 'check_suite']:
                # check_run and check_suite events have PR data in check_run/check_suite -> pull_requests array
                # Multiple PRs can be associated with a single check, so we update all of them
                check_data = payload.get('check_run') or payload.get('check_suite', {})
                pull_requests = check_data.get('pull_requests', [])
                repo_data = payload.get('repository', {})
                repo_owner = repo_data.get('owner', {}).get('login')
                repo_name = repo_data.get('name')
                
                for pr_data in pull_requests:
                    pr_number = pr_data.get('number')
                    if all([pr_number, repo_owner, repo_name]):
                        prs_to_update.append((pr_number, repo_owner, repo_name))
            
            if not prs_to_update:
                # If we can't extract PR info, just acknowledge the event
                return Response.new(
                    json.dumps({
                        'success': True,
                        'message': f'Received {event_type} event, insufficient PR data to update'
                    }),
                    {'headers': {'Content-Type': 'application/json'}}
                )
            
            # Update all tracked PRs associated with this event
            db = get_db(env)
            updated_prs = []
            
            # Step 1: Filter to only tracked PRs and collect their IDs
            tracked_prs = []  # List of (pr_number, repo_owner, repo_name, pr_id, pr_url)
            
            for pr_number, repo_owner, repo_name in prs_to_update:
                pr_url = f"https://github.com/{repo_owner}/{repo_name}/pull/{pr_number}"
                result = await db.prepare(
                    'SELECT id FROM prs WHERE pr_url = ?'
                ).bind(pr_url).first()
                
                if not result:
                    # PR not being tracked - skip it
                    print(f"Skipping untracked PR #{pr_number} in {event_type} event")
                    continue
                
                try:
                    result_dict = result.to_py()
                    pr_id = result_dict.get('id')
                    if not pr_id:
                        print(f"Error: Database result missing 'id' field for PR #{pr_number} in {repo_owner}/{repo_name} during {event_type} event")
                        continue
                    tracked_prs.append((pr_number, repo_owner, repo_name, pr_id, pr_url))
                except Exception as db_error:
                    print(f"Error parsing database result for PR #{pr_number} in {repo_owner}/{repo_name} during {event_type} event: {str(db_error)}")
                    continue
            
            if not tracked_prs:
                return Response.new(
                    json.dumps({
                        'success': True,
                        'message': f'Received {event_type} event for untracked PR(s), no updates performed'
                    }),
                    {'headers': {'Content-Type': 'application/json'}}
                )
            
            # Step 2: Batch fetch PR data from GitHub using GraphQL
            print(f"Batch fetching {len(tracked_prs)} PRs for {event_type} event")
            prs_to_fetch = [(repo_owner, repo_name, pr_number) for pr_number, repo_owner, repo_name, pr_id, pr_url in tracked_prs]
            
            # Get token from env if available (for webhook-triggered updates)
            webhook_token = getattr(env, 'GITHUB_TOKEN', None)
            batch_results = await fetch_multiple_prs_batch(prs_to_fetch, webhook_token)
            
            # Step 3: Update database with fetched data
            for pr_number, repo_owner, repo_name, pr_id, pr_url in tracked_prs:
                key = (repo_owner, repo_name, pr_number)
                fetched_pr_data = batch_results.get(key)
                
                if fetched_pr_data:
                    try:
                        await upsert_pr(db, pr_url, repo_owner, repo_name, pr_number, fetched_pr_data)
                        # Invalidate caches to force fresh analysis
                        await invalidate_readiness_cache(env, pr_id)
                        await invalidate_timeline_cache(env, repo_owner, repo_name, pr_number)
                        updated_prs.append({'pr_id': pr_id, 'pr_number': pr_number})
                    except Exception as update_error:
                        print(f"Error updating PR #{pr_number} in {repo_owner}/{repo_name}: {str(update_error)}")
                else:
                    print(f"Failed to fetch PR data for #{pr_number} in {repo_owner}/{repo_name} during {event_type} event")
            
            # Return response with info about all updated PRs
            if updated_prs:
                return Response.new(
                    json.dumps({
                        'success': True,
                        'event': f'{event_type}_processed',
                        'updated_prs': updated_prs,
                        'message': f'Updated {len(updated_prs)} PR(s) from {event_type} event (batch API call)'
                    }),
                    {'headers': {'Content-Type': 'application/json'}}
                )
            else:
                # No tracked PRs were updated
                return Response.new(
                    json.dumps({
                        'success': True,
                        'message': f'Received {event_type} event for untracked PR(s), no updates performed'
                    }),
                    {'headers': {'Content-Type': 'application/json'}}
                )
        
        # Unknown event type
        return Response.new(
            json.dumps({
                'success': True,
                'message': f'Received {event_type} event, no handler configured'
            }),
            {'headers': {'Content-Type': 'application/json'}}
        )
        
    except Exception as e:
        print(f"Error handling webhook: {type(e).__name__}: {str(e)}")
        return Response.new(
            json.dumps({'error': f"{type(e).__name__}: {str(e)}"}),
            {'status': 500, 'headers': {'Content-Type': 'application/json'}}
        )

async def handle_pr_timeline(request, env, path):
    """
    GET /api/prs/{id}/timeline
    Fetch and return the full timeline for a PR
    
    Features:
    - Application-level rate limiting (10 requests/minute per IP)
    """
    try:
        # Extract PR ID from path: /api/prs/123/timeline
        pr_id = path.split('/')[3]  # Split by / and get the ID
        
        # Get client IP for rate limiting
        client_ip = (
            request.headers.get('cf-connecting-ip') or
            (request.headers.get('x-forwarded-for') or '').split(',')[0].strip() or
            request.headers.get('x-real-ip') or
            'unknown'
        )
        
        # Check rate limit
        allowed, retry_after = check_rate_limit(client_ip)
        if not allowed:
            return Response.new(
                json.dumps({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Please try again in {retry_after} seconds.',
                    'retry_after': retry_after
                }),
                {
                    'status': 429,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Retry-After': str(retry_after),
                        'X-RateLimit-Limit': str(_READINESS_RATE_LIMIT),
                        'X-RateLimit-Window': str(_READINESS_RATE_WINDOW)
                    }
                }
            )
        
        # Get PR details from database
        db = get_db(env)
        result = await db.prepare(
            'SELECT * FROM prs WHERE id = ?'
        ).bind(pr_id).first()
        
        if not result:
            return Response.new(json.dumps({'error': 'PR not found'}), 
                              {'status': 404, 'headers': {'Content-Type': 'application/json'}})
        
        pr = result.to_py()
        
        # Fetch timeline data from GitHub
        github_token = request.headers.get('x-github-token') or getattr(env, 'GITHUB_TOKEN', None)

        timeline_data = await fetch_pr_timeline_data(
            env,
            pr['repo_owner'],
            pr['repo_name'],
            pr['pr_number'],
            github_token
        )
        
        # Build unified timeline
        timeline = build_pr_timeline(timeline_data)
        
        # Convert datetime objects to ISO strings for JSON serialization
        timeline_json = []
        for event in timeline:
            event_copy = event.copy()
            event_copy['timestamp'] = event['timestamp'].isoformat()
            timeline_json.append(event_copy)
        
        return Response.new(json.dumps({
            'pr': {
                'id': pr['id'],
                'title': pr['title'],
                'author': pr['author_login'],
                'repo': f"{pr['repo_owner']}/{pr['repo_name']}",
                'number': pr['pr_number']
            },
            'timeline': timeline_json,
            'event_count': len(timeline_json)
        }), 
                          {'headers': {'Content-Type': 'application/json'}})
    except Exception as e:
        return Response.new(json.dumps({'error': f"{type(e).__name__}: {str(e)}"}), 
                          {'status': 500, 'headers': {'Content-Type': 'application/json'}})

async def handle_pr_review_analysis(request, env, path):
    """
    GET /api/prs/{id}/review-analysis
    Analyze PR review progress and health
    
    Features:
    - Application-level rate limiting (10 requests/minute per IP)
    """
    try:
        # Extract PR ID from path: /api/prs/123/review-analysis
        pr_id = path.split('/')[3]
        
        # Get client IP for rate limiting
        client_ip = (
            request.headers.get('cf-connecting-ip') or
            (request.headers.get('x-forwarded-for') or '').split(',')[0].strip() or
            request.headers.get('x-real-ip') or
            'unknown'
        )
        
        # Check rate limit
        allowed, retry_after = check_rate_limit(client_ip)
        if not allowed:
            return Response.new(
                json.dumps({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Please try again in {retry_after} seconds.',
                    'retry_after': retry_after
                }),
                {
                    'status': 429,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Retry-After': str(retry_after),
                        'X-RateLimit-Limit': str(_READINESS_RATE_LIMIT),
                        'X-RateLimit-Window': str(_READINESS_RATE_WINDOW)
                    }
                }
            )
        
        # Get PR details from database
        db = get_db(env)
        result = await db.prepare(
            'SELECT * FROM prs WHERE id = ?'
        ).bind(pr_id).first()
        
        if not result:
            return Response.new(json.dumps({'error': 'PR not found'}), 
                              {'status': 404, 'headers': {'Content-Type': 'application/json'}})
        
        pr = result.to_py()
        
        # Fetch timeline data from GitHub
        github_token = request.headers.get('x-github-token') or getattr(env, 'GITHUB_TOKEN', None)

        timeline_data = await fetch_pr_timeline_data(env, 
            pr['repo_owner'],
            pr['repo_name'],
            pr['pr_number'],
            github_token
        )
        
        # Build unified timeline
        timeline = build_pr_timeline(timeline_data)
        
        # Analyze review progress
        review_data = analyze_review_progress(timeline, pr['author_login'])
        
        # Classify review health
        classification, score = classify_review_health(review_data)
        
        return Response.new(json.dumps({
            'pr': {
                'id': pr['id'],
                'title': pr['title'],
                'author': pr['author_login'],
                'repo': f"{pr['repo_owner']}/{pr['repo_name']}",
                'number': pr['pr_number']
            },
            'review_analysis': {
                'classification': classification,
                'score': score,
                'score_display': f"{score}%",
                'total_feedback': review_data['total_feedback_count'],
                'responded_feedback': review_data['responded_count'],
                'response_rate': review_data['response_rate'],
                'response_rate_display': f"{int(review_data['response_rate'] * 100)}%",
                'awaiting_author': review_data['awaiting_author'],
                'awaiting_reviewer': review_data['awaiting_reviewer'],
                'stale_feedback_count': len(review_data['stale_feedback']),
                'stale_feedback': review_data['stale_feedback'],
                'latest_review_state': review_data['latest_review_state'],
                'last_reviewer_action': review_data['last_reviewer_action'],
                'last_author_action': review_data['last_author_action']
            },
            'feedback_loops': review_data['feedback_loops']
        }), 
                          {'headers': {'Content-Type': 'application/json'}})
    except Exception as e:
        return Response.new(json.dumps({'error': f"{type(e).__name__}: {str(e)}"}), 
                          {'status': 500, 'headers': {'Content-Type': 'application/json'}})

async def _run_readiness_analysis(env, pr, pr_id, github_token):
    """
    Compute PR readiness analysis and cache the result.
    
    Shared logic used by handle_add_pr (auto-analysis on single PR add)
    and handle_pr_readiness (on-demand readiness endpoint).
    
    Args:
        env: Worker environment
        pr: PR data dict (from database SELECT *)
        pr_id: PR ID
        github_token: Optional GitHub token for API calls
    
    Returns:
        Dict containing readiness analysis data, or None if analysis fails
    """
    try:
        # Normalize pr_id to str so cache keys are consistent regardless of
        # whether the caller passes an int (handle_add_pr) or str (handle_pr_readiness)
        pr_id = str(pr_id)
        
        # Fetch timeline data from GitHub
        timeline_data = await fetch_pr_timeline_data(
            env,
            pr['repo_owner'],
            pr['repo_name'],
            pr['pr_number'],
            github_token
        )
        
        # Calculate and update review_status from timeline data
        # This ensures the database has the latest review status without making duplicate API calls
        original_review_status = pr.get('review_status', 'pending')
        review_status = calculate_review_status(timeline_data.get('reviews', []))
        if review_status != original_review_status:
            # Update review_status in database only if it actually changed
            db = get_db(env)
            await db.prepare(
                'UPDATE prs SET review_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?'
            ).bind(review_status, pr_id).run()
            pr['review_status'] = review_status
        
        # Build unified timeline
        timeline = build_pr_timeline(timeline_data)
        
        # Analyze review progress
        review_data = analyze_review_progress(timeline, pr['author_login'])
        
        # Classify review health
        review_classification, review_score = classify_review_health(review_data)
        
        # Calculate combined readiness
        readiness = calculate_pr_readiness(pr, review_classification, review_score)
        
        # Build response data with percentage formatting
        response_data = {
            'pr': {
                'id': pr['id'],
                'title': pr['title'],
                'author': pr['author_login'],
                'repo': f"{pr['repo_owner']}/{pr['repo_name']}",
                'number': pr['pr_number'],
                'state': pr['state'],
                'is_merged': pr['is_merged'] == 1,
                'mergeable_state': pr['mergeable_state'],
                'files_changed': pr['files_changed']
            },
            'readiness': {
                **readiness,
                'overall_score_display': f"{readiness['overall_score']}%",
                'ci_score_display': f"{readiness['ci_score']}%",
                'review_score_display': f"{readiness.get('review_score', review_score)}%"
            },
            'review_health': {
                'classification': review_classification,
                'score': review_score,
                'score_display': f"{review_score}%",
                'total_feedback': review_data['total_feedback_count'],
                'responded_feedback': review_data['responded_count'],
                'response_rate': review_data['response_rate'],
                'response_rate_display': f"{int(review_data['response_rate'] * 100)}%",
                'stale_feedback_count': len(review_data['stale_feedback']),
                'stale_feedback': review_data['stale_feedback']
            },
            'ci_checks': {
                'passed': pr['checks_passed'],
                'failed': pr['checks_failed'],
                'skipped': pr['checks_skipped']
            }
        }
        
        # Cache the result
        await set_readiness_cache(env, pr_id, response_data)
        
        return response_data
    except Exception as e:
        print(f"Error running readiness analysis for PR {pr_id}: {type(e).__name__}: {str(e)}")
        return None


async def handle_pr_readiness(request, env, path):
    """
    GET /api/prs/{id}/readiness
    Calculate overall PR readiness combining CI and review health
    
    Features:
    - Response caching (10 minutes TTL)
    - Cache invalidation on PR refresh
    - No app-level rate limiting: the endpoint serves all PRs (including "Analyze All")
      without artificial throttling. GitHub API rate limits still apply.
    """
    try:
        # Extract PR ID from path: /api/prs/123/readiness
        pr_id = path.split('/')[3]
        
        # Check cache first
        cached_result = await get_readiness_cache(env, pr_id)
        if cached_result:
            # Return cached response with cache headers
            return Response.new(
                json.dumps(cached_result),
                {
                    'headers': {
                        'Content-Type': 'application/json',
                        'X-Cache': 'HIT',
                        'Cache-Control': f'private, max-age={_READINESS_CACHE_TTL}'
                    }
                }
            )
        
        # Get PR details from database
        db = get_db(env)
        result = await db.prepare(
            'SELECT * FROM prs WHERE id = ?'
        ).bind(pr_id).first()
        
        if not result:
            return Response.new(json.dumps({'error': 'PR not found'}), 
                              {'status': 404, 'headers': {'Content-Type': 'application/json'}})
        
        pr = result.to_py()
        
        # Fetch timeline data from GitHub
        github_token = request.headers.get('x-github-token') or getattr(env, 'GITHUB_TOKEN', None)
        
        # Run readiness analysis
        response_data = await _run_readiness_analysis(env, pr, pr_id, github_token)
        
        if response_data is None:
            return Response.new(json.dumps({'error': 'Failed to compute readiness analysis'}),
                              {'status': 500, 'headers': {'Content-Type': 'application/json'}})
        
        return Response.new(
            json.dumps(response_data),
            {
                'headers': {
                    'Content-Type': 'application/json',
                    'X-Cache': 'MISS',
                    'Cache-Control': f'private, max-age={_READINESS_CACHE_TTL}'
                }
            }
        )
    except Exception as e:
        return Response.new(json.dumps({'error': f"{type(e).__name__}: {str(e)}"}), 
                          {'status': 500, 'headers': {'Content-Type': 'application/json'}})



async def handle_scheduled_refresh(env):
    """
    Hourly scheduled task: refresh all PRs in the database with minimal API calls.

    Uses the GraphQL batch API to update up to 50 PRs per request, covering all
    tracked PRs in the fewest possible round-trips.  Closed/merged PRs are
    removed from the database automatically.
    """
    token = getattr(env, 'GITHUB_TOKEN', None)

    try:
        db = get_db(env)

        # Fetch only the fields needed to build the batch request
        stmt = db.prepare('SELECT id, pr_url, repo_owner, repo_name, pr_number FROM prs')
        result = await stmt.all()

        if not result or not result.results:
            print("Scheduled refresh: no PRs in database, nothing to do")
            return

        rows = [row.to_py() if hasattr(row, 'to_py') else dict(row) for row in result.results]
        print(f"Scheduled refresh: updating {len(rows)} PR(s)")

        # Build lookup: (owner, repo, pr_number) -> (pr_id, pr_url)
        prs_to_fetch = []
        pr_lookup = {}
        for row in rows:
            key = (row['repo_owner'], row['repo_name'], row['pr_number'])
            prs_to_fetch.append(key)
            pr_lookup[key] = (row['id'], row['pr_url'])

        # Batch-fetch all PRs via GraphQL (50 per request)
        batch_results = await fetch_multiple_prs_batch(prs_to_fetch, token)

        updated = 0
        removed = 0
        errors = 0

        for (owner, repo, pr_number), pr_data in batch_results.items():
            pr_id, pr_url = pr_lookup[(owner, repo, pr_number)]

            if not pr_data:
                print(f"Scheduled refresh: failed to fetch {owner}/{repo}#{pr_number}")
                errors += 1
                continue

            # Remove PRs that are now closed or merged
            if pr_data.get('is_merged') or pr_data.get('state') == 'closed':
                await invalidate_readiness_cache(env, pr_id)
                await invalidate_timeline_cache(env, owner, repo, pr_number)
                await db.prepare('DELETE FROM prs WHERE id = ?').bind(pr_id).run()
                status_msg = 'merged' if pr_data.get('is_merged') else 'closed'
                print(f"Scheduled refresh: removed {status_msg} PR {owner}/{repo}#{pr_number}")
                removed += 1
                continue

            try:
                await upsert_pr(db, pr_url, owner, repo, pr_number, pr_data)
                await invalidate_readiness_cache(env, pr_id)
                await invalidate_timeline_cache(env, owner, repo, pr_number)
                updated += 1
            except Exception as update_err:
                print(f"Scheduled refresh: error updating {owner}/{repo}#{pr_number}: {update_err}")
                errors += 1

        print(f"Scheduled refresh complete: updated={updated}, removed={removed}, errors={errors}")

    except Exception as e:
        print(f"Scheduled refresh failed: {type(e).__name__}: {e}")
