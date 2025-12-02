"""
Bug Hunts handler for the BLT API.
"""

from typing import Any, Dict
from ..utils import json_response, error_response, paginated_response, parse_pagination_params
from ..client import create_client


async def handle_hunts(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle bug hunt-related requests.
    
    Endpoints:
        GET /hunts - List all bug hunts
        GET /hunts/{id} - Get a specific bug hunt
        GET /hunts/active - Get currently active hunts
        GET /hunts/previous - Get past hunts
        GET /hunts/upcoming - Get upcoming hunts
    """
    client = create_client(env)
    
    # Get specific hunt
    if "id" in path_params:
        hunt_id = path_params["id"]
        
        # Validate ID is numeric
        if not hunt_id.isdigit():
            return error_response("Invalid hunt ID", status=400)
        
        result = await client.get_hunt(int(hunt_id))
        
        if result.get("error"):
            return error_response(
                result.get("message", "Hunt not found"),
                status=result.get("status", 404)
            )
        
        return json_response({
            "success": True,
            "data": result.get("data")
        })
    
    # Get active hunts
    if path.endswith("/active"):
        result = await client.get_hunts(active=True)
        
        if result.get("error"):
            return error_response(
                result.get("message", "Failed to fetch active hunts"),
                status=result.get("status", 500)
            )
        
        return json_response({
            "success": True,
            "filter": "active",
            "data": result.get("data", [])
        })
    
    # Get previous hunts
    if path.endswith("/previous"):
        result = await client.get_hunts(previous=True)
        
        if result.get("error"):
            return error_response(
                result.get("message", "Failed to fetch previous hunts"),
                status=result.get("status", 500)
            )
        
        return json_response({
            "success": True,
            "filter": "previous",
            "data": result.get("data", [])
        })
    
    # Get upcoming hunts
    if path.endswith("/upcoming"):
        result = await client.get_hunts(upcoming=True)
        
        if result.get("error"):
            return error_response(
                result.get("message", "Failed to fetch upcoming hunts"),
                status=result.get("status", 500)
            )
        
        return json_response({
            "success": True,
            "filter": "upcoming",
            "data": result.get("data", [])
        })
    
    # List all hunts with pagination
    page, per_page = parse_pagination_params(query_params)
    
    # Check for filter params
    active = query_params.get("active") == "true"
    previous = query_params.get("previous") == "true"
    upcoming = query_params.get("upcoming") == "true"
    
    result = await client.get_hunts(
        page=page,
        per_page=per_page,
        active=active,
        previous=previous,
        upcoming=upcoming
    )
    
    if result.get("error"):
        return error_response(
            result.get("message", "Failed to fetch hunts"),
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
