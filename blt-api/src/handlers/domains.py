"""
Domains handler for the BLT API.
"""

from typing import Any, Dict
from ..utils import json_response, error_response, paginated_response, parse_pagination_params
from ..client import create_client


async def handle_domains(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle domain-related requests.
    
    Endpoints:
        GET /domains - List domains with pagination
        GET /domains/{id} - Get a specific domain
        GET /domains/{id}/issues - Get issues for a domain
    """
    client = create_client(env)
    
    # Get specific domain
    if "id" in path_params:
        domain_id = path_params["id"]
        
        # Validate ID is numeric
        if not domain_id.isdigit():
            return error_response("Invalid domain ID", status=400)
        
        # Check if requesting issues for domain
        if path.endswith("/issues"):
            page, per_page = parse_pagination_params(query_params)
            
            result = await client.get_issues(
                page=page,
                per_page=per_page,
                domain=domain_id
            )
            
            if result.get("error"):
                return error_response(
                    result.get("message", "Failed to fetch domain issues"),
                    status=result.get("status", 500)
                )
            
            data = result.get("data", {})
            
            if isinstance(data, dict) and "results" in data:
                return json_response({
                    "success": True,
                    "domain_id": int(domain_id),
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
            
            return json_response({
                "success": True,
                "domain_id": int(domain_id),
                "data": data
            })
        
        # Get domain details
        result = await client.get_domain(int(domain_id))
        
        if result.get("error"):
            return error_response(
                result.get("message", "Domain not found"),
                status=result.get("status", 404)
            )
        
        return json_response({
            "success": True,
            "data": result.get("data")
        })
    
    # List domains with pagination
    page, per_page = parse_pagination_params(query_params)
    
    result = await client.get_domains(page=page, per_page=per_page)
    
    if result.get("error"):
        return error_response(
            result.get("message", "Failed to fetch domains"),
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
