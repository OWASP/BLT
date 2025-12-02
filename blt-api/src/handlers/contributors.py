"""
Contributors handler for the BLT API.
"""

from typing import Any, Dict
from ..utils import json_response, error_response, paginated_response, parse_pagination_params
from ..client import create_client


async def handle_contributors(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle contributor-related requests.
    
    Endpoints:
        GET /contributors - List contributors with pagination
        GET /contributors/{id} - Get a specific contributor
    """
    client = create_client(env)
    
    # Get specific contributor
    if "id" in path_params:
        contributor_id = path_params["id"]
        
        # Validate ID is numeric
        if not contributor_id.isdigit():
            return error_response("Invalid contributor ID", status=400)
        
        # Note: This might need a specific endpoint in BLT backend
        # For now, we'll try to get from the contributors list
        result = await client.get_contributors()
        
        if result.get("error"):
            return error_response(
                result.get("message", "Contributor not found"),
                status=result.get("status", 404)
            )
        
        data = result.get("data", [])
        
        # Try to find the specific contributor
        if isinstance(data, list):
            for contributor in data:
                if str(contributor.get("id")) == contributor_id or str(contributor.get("github_id")) == contributor_id:
                    return json_response({
                        "success": True,
                        "data": contributor
                    })
        
        return error_response("Contributor not found", status=404)
    
    # List contributors with pagination
    page, per_page = parse_pagination_params(query_params)
    
    result = await client.get_contributors(page=page, per_page=per_page)
    
    if result.get("error"):
        return error_response(
            result.get("message", "Failed to fetch contributors"),
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
