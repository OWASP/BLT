"""
Stats handler for the BLT API.
"""

from typing import Any, Dict
from ..utils import json_response, error_response
from ..client import create_client


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
    client = create_client(env)
    
    result = await client.get_stats()
    
    if result.get("error"):
        return error_response(
            result.get("message", "Failed to fetch statistics"),
            status=result.get("status", 500)
        )
    
    data = result.get("data", {})
    
    return json_response({
        "success": True,
        "data": {
            "bugs": data.get("bugs", 0),
            "users": data.get("users", 0),
            "hunts": data.get("hunts", 0),
            "domains": data.get("domains", 0)
        },
        "description": {
            "bugs": "Total number of bugs reported",
            "users": "Total number of registered users",
            "hunts": "Total number of bug hunts",
            "domains": "Total number of tracked domains"
        }
    })
