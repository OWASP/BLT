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
        
        existing_tables = [row['name'] for row in result.results] if result.results else []
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        is_initialized = len(missing_tables) == 0
        return is_initialized, missing_tables
        
    except Exception as e:
        raise Exception(f"Failed to check database initialization: {str(e)}")


def get_db(env):
    """Helper to get DB binding from env, handling different env types.
    
    Raises an exception if database is not configured.
    """
    # Try common binding names
    for name in ['pr_tracker', 'DB']:
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


async def get_db_safe(env):
    """Get database and verify it's properly initialized.
    
    Args:
        env: Environment bindings
    
    Returns:
        The database binding
    
    Raises:
        Exception: If database is not configured or not initialized
    """
    db = get_db(env)
    
    is_initialized, missing_tables = await check_db_initialized(db)
    
    if not is_initialized:
        raise Exception(
            f"Database is not initialized. Missing tables: {', '.join(missing_tables)}. "
            "Please run migrations first."
        )
    
    return db