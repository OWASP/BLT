"""
Users handler for the BLT API.
"""

from typing import Any, Dict
from ..utils import json_response, error_response, paginated_response, parse_pagination_params
from ..client import create_client


async def handle_users(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle user-related requests.
    
    Endpoints:
        GET /users - List users with pagination
        GET /users/{id} - Get a specific user
        GET /users/{id}/profile - Get user profile details
    """
    client = create_client(env)
    
    # Get specific user
    if "id" in path_params:
        user_id = path_params["id"]
        
        # Validate ID is numeric
        if not user_id.isdigit():
            return error_response("Invalid user ID", status=400)
        
        result = await client.get_user(int(user_id))
        
        if result.get("error"):
            return error_response(
                result.get("message", "User not found"),
                status=result.get("status", 404)
            )
        
        return json_response({
            "success": True,
            "data": result.get("data")
        })
    
    # List users with pagination
    page, per_page = parse_pagination_params(query_params)
    
    result = await client.get_users(page=page, per_page=per_page)
    
    if result.get("error"):
        return error_response(
            result.get("message", "Failed to fetch users"),
            status=result.get("status", 500)
        )
    
    data = result.get("data", {})
    
    # Handle paginated response
    if isinstance(data, dict) and "results" in data:
        return json_response({
            "success": True,
            "data": data.get("results", []),
            "pagination": {
                "page": page,
                "per_page": per_page,
                "count": len(data.get("results", [])),
                "total": data.get("count"),
                "next": data.get("next"),
                "previous": data.get("previous")
            }
        })
    
    if isinstance(data, list):
        return paginated_response(data, page=page, per_page=per_page)
    
    return json_response({
        "success": True,
        "data": data
    })
