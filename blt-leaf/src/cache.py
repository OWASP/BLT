"""Caching and rate limiting functionality"""

from js import Date

# In-memory cache for rate limit data (per worker isolate)
_rate_limit_cache = {
    'data': None,
    'timestamp': 0
}
# Cache TTL in seconds (5 minutes)
_RATE_LIMIT_CACHE_TTL = 300

# Application-level rate limiting for readiness endpoints
# Tracks requests per IP address with sliding window
_readiness_rate_limit = {
    # Structure: {'ip_address': {'count': int, 'window_start': float}}
}
# Rate limit: 10 requests per minute per IP for readiness endpoints
_READINESS_RATE_LIMIT = 10
_READINESS_RATE_WINDOW = 60  # seconds

# In-memory cache for readiness results
# Invalidated when PR is manually refreshed
_readiness_cache = {
    # Structure: {pr_id: {'data': dict, 'timestamp': float}}
}
# Cache TTL in seconds (10 minutes)
_READINESS_CACHE_TTL = 600

# In-memory cache for timeline data
# Reduces redundant API calls across timeline/review-analysis/readiness endpoints
_timeline_cache = {
    # Structure: {cache_key: {'data': dict, 'timestamp': float}}
    # cache_key format: "{owner}/{repo}/{pr_number}"
}
# Cache TTL in seconds (30 minutes - timeline data changes less frequently)
_TIMELINE_CACHE_TTL = 1800


def check_rate_limit(ip_address):
    """Check if request from IP is within rate limit for readiness endpoints.
    
    Args:
        ip_address: Client IP address
        
    Returns:
        Tuple of (allowed: bool, retry_after: int)
        - allowed: True if request is allowed, False if rate limited
        - retry_after: Seconds to wait before retrying (0 if allowed)
    """
    global _readiness_rate_limit
    
    current_time = Date.now() / 1000  # Convert milliseconds to seconds
    
    if ip_address not in _readiness_rate_limit:
        _readiness_rate_limit[ip_address] = {
            'count': 1,
            'window_start': current_time
        }
        print(f"Rate limit: New IP {ip_address} - count: 1")
        return (True, 0)
    
    rate_data = _readiness_rate_limit[ip_address]
    window_elapsed = current_time - rate_data['window_start']
    
    # Reset window if expired
    if window_elapsed >= _READINESS_RATE_WINDOW:
        _readiness_rate_limit[ip_address] = {
            'count': 1,
            'window_start': current_time
        }
        print(f"Rate limit: Window reset for {ip_address} - count: 1")
        return (True, 0)
    
    # Check if within limit
    if rate_data['count'] < _READINESS_RATE_LIMIT:
        rate_data['count'] += 1
        print(f"Rate limit: {ip_address} - count: {rate_data['count']}/{_READINESS_RATE_LIMIT}")
        return (True, 0)
    
    # Rate limited - calculate retry_after
    retry_after = int(_READINESS_RATE_WINDOW - window_elapsed) + 1
    print(f"Rate limit: EXCEEDED for {ip_address} - retry after {retry_after}s")
    return (False, retry_after)


async def get_readiness_cache(env, pr_id):
    """Get cached readiness result for a PR if still valid.
    
    First checks in-memory cache, then falls back to database if not found.
    
    Args:
        env: Worker environment with database binding
        pr_id: PR ID
        
    Returns:
        Cached data dict if valid, None if expired or not found
    """
    global _readiness_cache
    
    # Import here to avoid circular dependency
    from database import load_readiness_from_db
    
    # Check in-memory cache first
    if pr_id in _readiness_cache:
        cache_entry = _readiness_cache[pr_id]
        current_time = Date.now() / 1000
        
        # Check if cache is still valid
        if (current_time - cache_entry['timestamp']) < _READINESS_CACHE_TTL:
            age = int(current_time - cache_entry['timestamp'])
            print(f"Cache: HIT (memory) for PR {pr_id} (age: {age}s)")
            return cache_entry['data']
        
        # Cache expired - remove it
        del _readiness_cache[pr_id]
        print(f"Cache: MISS (memory expired) for PR {pr_id}")
    else:
        print(f"Cache: MISS (memory) for PR {pr_id}")
    
    # Fall back to database
    db_data = await load_readiness_from_db(env, pr_id)
    if db_data:
        # Store in memory cache for faster subsequent access
        current_time = Date.now() / 1000
        _readiness_cache[pr_id] = {
            'data': db_data,
            'timestamp': current_time
        }
        print(f"Cache: HIT (database) for PR {pr_id} - loaded into memory")
        return db_data
    
    print(f"Cache: MISS (database) for PR {pr_id}")
    return None


async def set_readiness_cache(env, pr_id, data):
    """Cache readiness result for a PR in both memory and database.
    
    Args:
        env: Worker environment with database binding
        pr_id: PR ID
        data: Readiness data to cache
    """
    global _readiness_cache
    
    # Import here to avoid circular dependency
    from database import save_readiness_to_db
    
    # Store in memory cache
    current_time = Date.now() / 1000
    _readiness_cache[pr_id] = {
        'data': data,
        'timestamp': current_time
    }
    print(f"Cache: Stored result (memory) for PR {pr_id}")
    
    # Also save to database for persistence
    await save_readiness_to_db(env, pr_id, data)


async def invalidate_readiness_cache(env, pr_id):
    """Invalidate cached readiness result for a PR in both memory and database.
    
    Args:
        env: Worker environment with database binding
        pr_id: PR ID
    """
    global _readiness_cache
    
    # Import here to avoid circular dependency
    from database import delete_readiness_from_db
    
    # Remove from memory cache
    if pr_id in _readiness_cache:
        del _readiness_cache[pr_id]
        print(f"Cache: Invalidated (memory) for PR {pr_id}")
    
    # Also remove from database
    await delete_readiness_from_db(env, pr_id)


def get_timeline_cache_key(owner, repo, pr_number):
    """Generate cache key for timeline data"""
    return f"{owner}/{repo}/{pr_number}"


def get_timeline_cache(owner, repo, pr_number):
    """Get cached timeline data if still valid.
    
    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
        
    Returns:
        Cached timeline data dict if valid, None if expired or not found
    """
    global _timeline_cache
    
    cache_key = get_timeline_cache_key(owner, repo, pr_number)
    
    if cache_key in _timeline_cache:
        cache_entry = _timeline_cache[cache_key]
        current_time = Date.now() / 1000
        
        # Check if cache is still valid
        if (current_time - cache_entry['timestamp']) < _TIMELINE_CACHE_TTL:
            age = int(current_time - cache_entry['timestamp'])
            print(f"Timeline Cache: HIT for {cache_key} (age: {age}s)")
            return cache_entry['data']
        
        # Cache expired - remove it
        del _timeline_cache[cache_key]
        print(f"Timeline Cache: MISS (expired) for {cache_key}")
    else:
        print(f"Timeline Cache: MISS for {cache_key}")
    
    return None


def set_timeline_cache(owner, repo, pr_number, data):
    """Cache timeline data.
    
    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
        data: Timeline data to cache
    """
    global _timeline_cache
    
    cache_key = get_timeline_cache_key(owner, repo, pr_number)
    current_time = Date.now() / 1000
    
    _timeline_cache[cache_key] = {
        'data': data,
        'timestamp': current_time
    }
    print(f"Timeline Cache: Stored for {cache_key}")


def invalidate_timeline_cache(owner, repo, pr_number):
    """Invalidate cached timeline data for a PR.
    
    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
    """
    global _timeline_cache
    
    cache_key = get_timeline_cache_key(owner, repo, pr_number)
    
    if cache_key in _timeline_cache:
        del _timeline_cache[cache_key]
        print(f"Timeline Cache: Invalidated for {cache_key}")


# Export cache dict for rate limit handler access
def get_rate_limit_cache():
    """Get the rate limit cache dict"""
    global _rate_limit_cache
    return _rate_limit_cache
