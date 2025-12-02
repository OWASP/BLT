"""
Issues handler for the BLT API.
"""

from typing import Any, Dict
from ..utils import json_response, error_response, paginated_response, parse_pagination_params, parse_json_body
from ..client import create_client


async def handle_issues(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle issues-related requests.
    
    Endpoints:
        GET /issues - List issues with pagination and filters
        GET /issues/{id} - Get a specific issue
        POST /issues - Create a new issue
        GET /issues/search - Search issues
    """
    client = create_client(env)
    method = str(request.method).upper()
    
    # Get specific issue
    if "id" in path_params:
        issue_id = path_params["id"]
        
        # Validate ID is numeric
        if not issue_id.isdigit():
            return error_response("Invalid issue ID", status=400)
        
        result = await client.get_issue(int(issue_id))
        
        if result.get("error"):
            return error_response(
                result.get("message", "Issue not found"),
                status=result.get("status", 404)
            )
        
        return json_response({
            "success": True,
            "data": result.get("data")
        })
    
    # Search issues
    if path.endswith("/search"):
        query = query_params.get("q", "")
        if not query:
            return error_response("Search query 'q' is required", status=400)
        
        limit = query_params.get("limit", "10")
        try:
            limit_int = min(max(int(limit), 1), 100)
        except ValueError:
            limit_int = 10
        
        result = await client.search_issues(query, limit=limit_int)
        
        if result.get("error"):
            return error_response(
                result.get("message", "Search failed"),
                status=result.get("status", 500)
            )
        
        return json_response({
            "success": True,
            "query": query,
            "data": result.get("data")
        })
    
    # Create issue
    if method == "POST":
        body = await parse_json_body(request)
        
        if not body:
            return error_response("Request body is required", status=400)
        
        # Validate required fields
        required_fields = ["url", "description"]
        missing_fields = [f for f in required_fields if f not in body]
        
        if missing_fields:
            return error_response(
                f"Missing required fields: {', '.join(missing_fields)}",
                status=400
            )
        
        result = await client.create_issue(body)
        
        if result.get("error"):
            return error_response(
                result.get("message", "Failed to create issue"),
                status=result.get("status", 400)
            )
        
        return json_response({
            "success": True,
            "message": "Issue created successfully",
            "data": result.get("data")
        }, status=201)
    
    # List issues with pagination
    page, per_page = parse_pagination_params(query_params)
    
    result = await client.get_issues(
        page=page,
        per_page=per_page,
        status=query_params.get("status"),
        domain=query_params.get("domain"),
        search=query_params.get("search")
    )
    
    if result.get("error"):
        return error_response(
            result.get("message", "Failed to fetch issues"),
            status=result.get("status", 500)
        )
    
    data = result.get("data", {})
    
    # Handle paginated response from Django REST Framework
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
    
    # Handle list response
    if isinstance(data, list):
        return paginated_response(data, page=page, per_page=per_page)
    
    return json_response({
        "success": True,
        "data": data
    })
