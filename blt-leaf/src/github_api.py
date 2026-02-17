"""GitHub API interactions"""

import json
import asyncio
from js import fetch, Headers, Object
from pyodide.ffi import to_js
from .cache import get_timeline_cache, set_timeline_cache


async def fetch_with_headers(url, headers=None, token=None):
    """Helper to fetch with proper header handling using pyodide.ffi.to_js"""
    if not headers:
        headers = {}
        
    if 'User-Agent' not in headers:
        headers['User-Agent'] = 'PR-Tracker/1.0'        
    if token:
        headers['Authorization'] = f'Bearer {token}'

    options = to_js({
        "method": "GET",
        "headers": headers
    }, dict_converter=Object.fromEntries)
    
    response = await fetch(url, options)
    
    # Log GitHub API call with rate limit information
    # Check if URL starts with GitHub API domain for logging purposes only
    if url.startswith('https://api.github.com/'):
        rate_limit = response.headers.get('x-ratelimit-limit')
        rate_remaining = response.headers.get('x-ratelimit-remaining')
        rate_reset = response.headers.get('x-ratelimit-reset')
        print(f"GitHub API: {url} | Status: {response.status} | Rate Limit: {rate_remaining}/{rate_limit} remaining | Reset: {rate_reset}")
    
    return response


async def fetch_open_conversations_count(owner, repo, pr_number, token=None):
    """
    Fetch count of unresolved review conversations (threads) using GitHub GraphQL API.
    
    Supports pagination to handle PRs with more than 100 review threads.
    
    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: Pull request number
        token: Optional GitHub token for authentication
        
    Returns:
        int: Count of unresolved conversations, or 0 if error occurs
    """
    graphql_url = "https://api.github.com/graphql"
    
    # GraphQL query to fetch review threads with their resolved status and pagination
    query = """
    query($owner: String!, $repo: String!, $prNumber: Int!, $cursor: String) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $prNumber) {
          reviewThreads(first: 100, after: $cursor) {
            nodes {
              isResolved
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
      }
    }
    """
    
    headers = {
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json',
        'User-Agent': 'PR-Tracker/1.0'
    }
    
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    unresolved_count = 0
    cursor = None
    has_next_page = True
    
    try:
        # Paginate through all review threads
        while has_next_page:
            variables = {
                "owner": owner,
                "repo": repo,
                "prNumber": pr_number,
                "cursor": cursor
            }
            
            # Make GraphQL request
            options = to_js({
                "method": "POST",
                "headers": headers,
                "body": json.dumps({"query": query, "variables": variables})
            }, dict_converter=Object.fromEntries)
            
            response = await fetch(graphql_url, options)
            
            # Log GraphQL API call
            rate_limit = response.headers.get('x-ratelimit-limit')
            rate_remaining = response.headers.get('x-ratelimit-remaining')
            print(f"GitHub GraphQL API: Status: {response.status} | Rate Limit: {rate_remaining}/{rate_limit} remaining")
            
            if response.status != 200:
                print(f"Warning: GraphQL API returned status {response.status}")
                return unresolved_count  # Return count from previous pages
            
            result = (await response.json()).to_py()
            
            # Check for GraphQL errors
            if 'errors' in result:
                print(f"GraphQL errors: {result['errors']}")
                return unresolved_count  # Return count from previous pages
            
            # Extract unresolved conversations count from this page
            pull_request = result.get('data', {}).get('repository', {}).get('pullRequest')
            if not pull_request:
                print(f"Warning: No PR data in GraphQL response for {owner}/{repo}#{pr_number}")
                return unresolved_count
            
            review_threads_data = pull_request.get('reviewThreads', {})
            threads = review_threads_data.get('nodes', [])
            page_info = review_threads_data.get('pageInfo', {})
            
            # Count unresolved threads in this page
            unresolved_count += sum(1 for thread in threads if not thread.get('isResolved', False))
            
            # Check if there are more pages
            has_next_page = page_info.get('hasNextPage', False)
            cursor = page_info.get('endCursor')
            
            print(f"PR #{pr_number}: Page has {len(threads)} threads, {unresolved_count} total unresolved so far")
        
        print(f"PR #{pr_number}: Found {unresolved_count} total unresolved conversations")
        return unresolved_count
        
    except Exception as e:
        print(f"Error fetching open conversations for PR #{pr_number}: {str(e)}")
        return unresolved_count  # Return partial count if available


async def fetch_pr_data(owner, repo, pr_number, token=None):
    """
    Fetch PR data from GitHub API with parallel requests for optimal performance.
    
    Optimizations applied:
    - Reviews are NOT fetched here to avoid duplication with fetch_pr_timeline_data
    - Files list is NOT fetched since PR details already include 'changed_files' count
    - Checks and compare API calls are made in parallel for efficiency
    
    This reduces API calls from 5 to 3 per fetch (PR details + checks + compare).
    """
    headers = {
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
    }
        
    try:
        # Fetch PR details first (needed for head SHA)
        pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        pr_response = await fetch_with_headers(pr_url, headers, token)
        
        if pr_response.status != 200:
            return None
            
        pr_data = (await pr_response.json()).to_py()

        # Prepare URLs for parallel fetching
        # Note: We don't fetch reviews here to avoid duplication with fetch_pr_timeline_data
        # Note: We don't fetch files list since pr_data already includes 'changed_files' count
        # Reviews will be fetched by fetch_pr_timeline_data for timeline analysis
        checks_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{pr_data['head']['sha']}/check-runs"
        
        # Extract base and head branch information for comparison
        # To check if PR is behind base, we need to compare the branches (not SHAs)
        # Using branch refs ensures we compare the current state of the branches
        base_branch = pr_data['base']['ref']
        head_branch = pr_data['head']['ref']
        # For forks, we need to use the full ref format
        # Handle case where fork is deleted (repo is None)
        head_repo = pr_data['head'].get('repo')
        if head_repo and head_repo.get('owner'):
            head_full_ref = f"{head_repo['owner']['login']}:{head_branch}"
        else:
            # If fork is deleted, use just the branch name (comparison will likely fail but won't crash)
            print(f"Warning: PR #{pr_number} head repository is None (fork may be deleted)")
            head_full_ref = head_branch
        
        # Compare head...base to see how many commits base has that head doesn't
        compare_url = f"https://api.github.com/repos/{owner}/{repo}/compare/{head_full_ref}...{base_branch}"
        
        # Fetch checks and comparison in parallel using asyncio.gather
        # This reduces total fetch time from sequential sum to max single request time
        # Reviews are intentionally excluded to avoid duplicate API calls with fetch_pr_timeline_data
        # Files list is excluded since we only need the count which is in pr_data['changed_files']
        checks_data = {}
        compare_data = {}
        open_conversations_count = 0
        
        try:
            results = await asyncio.gather(
                fetch_with_headers(checks_url, headers, token),
                fetch_with_headers(compare_url, headers, token),
                fetch_open_conversations_count(owner, repo, pr_number, token),
                return_exceptions=True
            )
            
            # Process checks result
            if not isinstance(results[0], Exception) and results[0].status == 200:
                checks_data = (await results[0].json()).to_py()
            
            # Process compare result
            if not isinstance(results[1], Exception) and results[1].status == 200:
                compare_data = (await results[1].json()).to_py()
                print(f"Compare API success for PR #{pr_number}")
            elif not isinstance(results[1], Exception):
                # Log error if compare API fails
                print(f"Compare API failed for PR #{pr_number} with status {results[1].status}, URL: {compare_url}")
            else:
                print(f"Compare API exception for PR #{pr_number}: {results[1]}")
            
            # Process open conversations count result
            if not isinstance(results[2], Exception):
                open_conversations_count = results[2]
            else:
                print(f"Open conversations fetch exception for PR #{pr_number}: {results[2]}")
        except Exception as e:
            print(f"Error fetching PR data for #{pr_number}: {str(e)}")
        
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
        
        # Get commits count from pr_data (GitHub provides this)
        commits_count = pr_data.get('commits', 0)
        
        # Get behind_by count from compare data
        # When comparing head...base, ahead_by tells us how many commits base has that head doesn't
        behind_by = 0
        if compare_data:
            # Use ahead_by since we reversed the comparison (head...base)
            # Use 'or 0' to handle None values from GitHub API
            behind_by = compare_data.get('ahead_by') or 0
            print(f"PR #{pr_number}: Compare status={compare_data.get('status')}, ahead_by={compare_data.get('ahead_by')}, behind_by={compare_data.get('behind_by')}")
        
        # Review status will be set to 'pending' by default
        # It will be updated when timeline data is fetched by fetch_pr_timeline_data
        # This avoids duplicate API calls to the reviews endpoint
        review_status = 'pending'
        
        return {
            'title': pr_data.get('title', ''),
            'state': pr_data.get('state', ''),
            'is_merged': 1 if pr_data.get('merged', False) else 0,
            'mergeable_state': pr_data.get('mergeable_state', ''),
            'files_changed': pr_data.get('changed_files', 0),  # Use changed_files from PR data instead of fetching files list
            'author_login': pr_data['user']['login'],
            'author_avatar': pr_data['user']['avatar_url'],
            'repo_owner_avatar': pr_data.get('base', {}).get('repo', {}).get('owner', {}).get('avatar_url', ''),
            'checks_passed': checks_passed,
            'checks_failed': checks_failed,
            'checks_skipped': checks_skipped,
            'commits_count': commits_count,
            'behind_by': behind_by,
            'review_status': review_status,
            'last_updated_at': pr_data.get('updated_at', ''),
            'is_draft': 1 if pr_data.get('draft', False) else 0,
            'open_conversations_count': open_conversations_count
        }
    except Exception as e:
        # Return more informative error for debugging
        error_msg = f"Error fetching PR data: {str(e)}"
        # In Cloudflare Workers, console.error is preferred
        raise Exception(error_msg)


async def fetch_paginated_data(url, headers):
    """
    Fetch all pages of data from a GitHub API endpoint following Link headers
    
    Args:
        url: Initial URL to fetch
        headers: Headers object to use for requests
    
    Returns:
        List of all items across all pages
    """
    all_data = []
    current_url = url
    fetch_options = to_js({'headers': headers}, dict_converter=Object.fromEntries)
    
    while current_url:
        response = await fetch(current_url, fetch_options)
        
        # Log GitHub API call with rate limit information
        # Check if URL starts with GitHub API domain for logging purposes only
        if current_url.startswith('https://api.github.com/'):
            rate_limit = response.headers.get('x-ratelimit-limit')
            rate_remaining = response.headers.get('x-ratelimit-remaining')
            rate_reset = response.headers.get('x-ratelimit-reset')
            print(f"GitHub API: {current_url} | Status: {response.status} | Rate Limit: {rate_remaining}/{rate_limit} remaining | Reset: {rate_reset}")
        
        if not response.ok:
            status = getattr(response, 'status', 'unknown')
            status_text = getattr(response, 'statusText', '')
            raise Exception(
                f"GitHub API error: status={status} {status_text} url={current_url}"
            )
        
        page_data = (await response.json()).to_py()
        all_data.extend(page_data)
        
        # Check for Link header to get next page
        link_header = response.headers.get('link')
        current_url = None
        
        if link_header:
            # Parse Link header: <url>; rel="next", <url>; rel="last"
            links = link_header.split(',')
            for link in links:
                if 'rel="next"' in link:
                    # Extract URL from <url>
                    url_match = link.split(';')[0].strip()
                    if url_match.startswith('<') and url_match.endswith('>'):
                        current_url = url_match[1:-1]
                    break
    
    return all_data


async def fetch_pr_timeline_data(owner, repo, pr_number, github_token=None):
    """
    Fetch all timeline data for a PR: commits, reviews, review comments, issue comments
    
    Uses in-memory caching (30 min TTL) to avoid redundant API calls across endpoints.
    All 4 API calls are made in parallel for optimal performance.
    
    Note: Reviews are fetched here (not in fetch_pr_data) to avoid duplication.
    
    Returns dict with raw data from GitHub API:
    {
        'commits': [...],
        'reviews': [...],
        'review_comments': [...],
        'issue_comments': [...]
    }
    """
    # Check cache first
    cached_data = get_timeline_cache(owner, repo, pr_number)
    if cached_data:
        return cached_data
    
    base_url = 'https://api.github.com'
    
    # Prepare headers
    headers_dict = {
        'User-Agent': 'PR-Tracker/1.0',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
    }
    if github_token:
        headers_dict['Authorization'] = f'Bearer {github_token}'
    
    headers = Headers.new(to_js(headers_dict, dict_converter=Object.fromEntries))
    
    try:
        # Fetch all timeline data in parallel (with pagination)
        commits_url = f'{base_url}/repos/{owner}/{repo}/pulls/{pr_number}/commits?per_page=100'
        reviews_url = f'{base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews?per_page=100'
        review_comments_url = f'{base_url}/repos/{owner}/{repo}/pulls/{pr_number}/comments?per_page=100'
        issue_comments_url = f'{base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments?per_page=100'
        
        # Make truly parallel requests using asyncio.gather
        commits_data, reviews_data, review_comments_data, issue_comments_data = await asyncio.gather(
            fetch_paginated_data(commits_url, headers),
            fetch_paginated_data(reviews_url, headers),
            fetch_paginated_data(review_comments_url, headers),
            fetch_paginated_data(issue_comments_url, headers)
        )
        
        timeline_data = {
            'commits': commits_data,
            'reviews': reviews_data,
            'review_comments': review_comments_data,
            'issue_comments': issue_comments_data
        }
        
        # Cache the result for future requests
        set_timeline_cache(owner, repo, pr_number, timeline_data)
        
        return timeline_data
    except Exception as e:
        raise Exception(f"Error fetching timeline data: {str(e)}")


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
