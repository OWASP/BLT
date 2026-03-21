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
        bugs_result = await db.prepare('SELECT COUNT(*) as count FROM bugs').first()
        bugs_count = (await convert_single_d1_result(bugs_result)).get('count', 0)

        users_result = await db.prepare('SELECT COUNT(*) as count FROM users WHERE is_active = 1').first()
        users_count = (await convert_single_d1_result(users_result)).get('count', 0)

        domains_result = await db.prepare('SELECT COUNT(*) as count FROM domains WHERE is_active = 1').first()
        domains_count = (await convert_single_d1_result(domains_result)).get('count', 0)

        try:
            hunts_result = await db.prepare('SELECT COUNT(*) as count FROM hunts').first()
            hunts_count = (await convert_single_d1_result(hunts_result)).get('count', 0)
        except Exception as e:
            # Some environments may not have the hunts table yet.
            if 'no such table: hunts' in str(e).lower():
                hunts_count = 0
                logger.warning("Hunts table not found while fetching stats; defaulting hunts count to 0")
            else:
                raise

        payload = {
            "success": True,
            "data": {
                "bugs": bugs_count,
                "users": users_count,
                "domains": domains_count,
                "hunts": hunts_count,
            },
            "description": {
                "bugs": "Total number of bugs reported",
                "users": "Total number of registered users",
                "domains": "Total number of tracked domains",
                "hunts": "Total number of bug hunts",
            }
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
