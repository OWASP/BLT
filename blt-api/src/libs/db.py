import asyncio
import weakref
from typing import Optional

# Global cache for database initialization status.
# In Cloudflare Workers, global variables persist between requests on the same isolate.
_DB_INITIALIZED_CACHE: bool = False
_DB_INITIALIZED_LOCKS: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Lock]" = (
    weakref.WeakKeyDictionary()
)


def get_db_initialized_lock() -> asyncio.Lock:
    """Gets or creates an asyncio.Lock bound to the current running event loop."""
    loop = asyncio.get_running_loop()
    lock = _DB_INITIALIZED_LOCKS.get(loop)
    if lock is None:
        lock = asyncio.Lock()
        _DB_INITIALIZED_LOCKS[loop] = lock
    return lock


def reset_db_cache(loop: "Optional[asyncio.AbstractEventLoop]" = None) -> None:
    """Resets the database initialization cache state.
    
    If *loop* is provided, ONLY the lock for that specific loop is removed.
    The global cache flag is always reset to False to force a re-check.
    """
    global _DB_INITIALIZED_CACHE
    _DB_INITIALIZED_CACHE = False
    
    if loop is not None:
        _DB_INITIALIZED_LOCKS.pop(loop, None)
    else:
        _DB_INITIALIZED_LOCKS.clear()


def get_db(env):
    """Helper to get DB binding from env, handling different env types.
    
    Raises an exception if database is not configured.
    """
    # Try common binding names (based on wrangler.toml)
    for name in ['blt_api', 'DB']:
        # Try attribute access
        if hasattr(env, name):
            return getattr(env, name)
        # Try dict access
        if hasattr(env, '__getitem__'):
            try:
                return env[name]
            except (KeyError, TypeError):
                pass
    raise Exception("Database not configured in the environment.")


async def check_db_initialized(db):
    """Check if the database is initialized with required tables.
    
    Args:
        db: The D1 database binding
    
    Returns:
        tuple: (is_initialized: bool, missing_tables: list)
    
    Raises:
        Exception: If database query fails
    """
    required_tables = ['domains', 'tags', 'domain_tags']
    
    try:
        # Query sqlite_master to check for existing tables
        result = await db.prepare(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN (?, ?, ?)"
        ).bind(*required_tables).all()
        
        # D1 results are JavaScript proxy objects - convert safely
        existing_tables = []
        if hasattr(result, 'results'):
            results = result.results
            # Handle both Python list and JS proxy
            if hasattr(results, 'to_py'):
                results = results.to_py()
            for row in results:
                # Handle both dict and proxy object
                if isinstance(row, dict):
                    existing_tables.append(row.get('name'))
                elif hasattr(row, 'name'):
                    existing_tables.append(row.name)
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        is_initialized = len(missing_tables) == 0
        return is_initialized, missing_tables
        
    except Exception as e:
        raise Exception(f"Failed to check database initialization: {str(e)}")


async def get_db_safe(env):
    """Get database and verify it's properly initialized.
    
    Args:
        env: Environment bindings
    
    Returns:
        The database binding
    
    Raises:
        Exception: If database is not configured or not initialized
    """
    global _DB_INITIALIZED_CACHE
    
    db = get_db(env)
    
    # Fast path: already initialized
    if _DB_INITIALIZED_CACHE:
        return db
        
    # Slow path: need to check initialization, guarded by a lock to prevent race conditions
    async with get_db_initialized_lock():
        # Double-check after acquiring lock
        if not _DB_INITIALIZED_CACHE:
            is_initialized, missing_tables = await check_db_initialized(db)
            
            if not is_initialized:
                raise Exception(
                    f"Database is not initialized. Missing tables: {', '.join(missing_tables)}. "
                    "Please run migrations first."
                )
            
            _DB_INITIALIZED_CACHE = True
    
    return db