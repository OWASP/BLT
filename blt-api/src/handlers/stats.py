"""
Stats handler for the BLT API.
"""

import logging
from typing import Any, Dict
from utils import json_response, error_response, convert_single_d1_result
from libs.db import get_db_safe


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

        return json_response({
            "success": True,
            "data": {
                "bugs": bugs_count,
                "users": users_count,
                "domains": domains_count,
            },
            "description": {
                "bugs": "Total number of bugs reported",
                "users": "Total number of registered users",
                "domains": "Total number of tracked domains",
            }
        })
    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        return error_response(f"Error fetching stats: {str(e)}", status=500)
