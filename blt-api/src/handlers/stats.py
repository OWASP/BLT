"""
Stats handler for the BLT API.
"""

import logging
import time
from typing import Any, Dict
from utils import json_response, error_response, convert_single_d1_result
from libs.db import get_db_safe


# Lightweight server-side cache (per worker isolate) for /stats.
_STATS_CACHE: Dict[str, Any] = {
    "data": None,
    "expires_at": 0.0,
}
_DEFAULT_STATS_CACHE_TTL_SECONDS = 60

_TABLES_TO_COUNT = [
    "bugs",
    "bug_screenshots",
    "bug_tags",
    "bug_team_members",
    "domains",
    "domain_tags",
    "organization",
    "organization_integrations",
    "organization_managers",
    "organization_tags",
    "tags",
    "user_bug_flags",
    "user_bug_saves",
    "user_bug_upvotes",
    "user_follows",
    "users",
    "d1_migrations",
    "hunts",
]


async def handle_stats(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle statistics-related requests.
    
    Endpoints:
        GET /stats - Get overall platform statistics
    """
    logger = logging.getLogger(__name__)

    ttl_seconds = _DEFAULT_STATS_CACHE_TTL_SECONDS
    try:
        ttl_seconds = int(getattr(env, "STATS_CACHE_TTL_SECONDS", _DEFAULT_STATS_CACHE_TTL_SECONDS))
    except (TypeError, ValueError):
        ttl_seconds = _DEFAULT_STATS_CACHE_TTL_SECONDS

    now = time.time()
    cached_payload = _STATS_CACHE.get("data")
    cache_expires_at = float(_STATS_CACHE.get("expires_at", 0.0))
    if cached_payload is not None and now < cache_expires_at:
        return json_response(
            cached_payload,
            headers={
                "Cache-Control": f"public, s-maxage={ttl_seconds}, stale-while-revalidate=30",
                "X-Stats-Cache": "HIT",
            },
        )

    try:
        db = await get_db_safe(env)
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return error_response(f"Database connection error: {str(e)}", status=500)

    try:
        counts: Dict[str, int] = {}
        descriptions: Dict[str, str] = {}

        for table_name in _TABLES_TO_COUNT:
            try:
                result = await db.prepare(f"SELECT COUNT(*) as count FROM {table_name}").first()
                row = await convert_single_d1_result(result)
                counts[table_name] = int(row.get("count", 0))
            except Exception as e:
                if "no such table" in str(e).lower():
                    counts[table_name] = 0
                    logger.warning("Table not found while fetching stats: %s", table_name)
                else:
                    raise
            descriptions[table_name] = f"Row count for {table_name.replace('_', ' ')}"

        payload = {
            "success": True,
            "data": counts,
            "description": descriptions,
        }

        _STATS_CACHE["data"] = payload
        _STATS_CACHE["expires_at"] = now + max(0, ttl_seconds)

        return json_response(
            payload,
            headers={
                "Cache-Control": f"public, s-maxage={ttl_seconds}, stale-while-revalidate=30",
                "X-Stats-Cache": "MISS",
            },
        )
    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        return error_response(f"Error fetching stats: {str(e)}", status=500)
