"""
Organizations handler for the BLT API.
"""

from typing import Any, Dict
from ..utils import json_response, error_response, paginated_response, parse_pagination_params
from ..client import create_client


async def handle_organizations(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle organization-related requests.
    
    Endpoints:
        GET /organizations - List organizations with pagination
        GET /organizations/{id} - Get a specific organization
        GET /organizations/{id}/repos - Get organization repositories
        GET /organizations/{id}/projects - Get organization projects
    """
    client = create_client(env)
    
    # Get specific organization
    if "id" in path_params:
        org_id = path_params["id"]
        
        # Validate ID is numeric
        if not org_id.isdigit():
            return error_response("Invalid organization ID", status=400)
        
        # Check if requesting repos for organization
        if path.endswith("/repos"):
            result = await client.get_organization_repos(int(org_id))
            
            if result.get("error"):
                return error_response(
                    result.get("message", "Failed to fetch organization repositories"),
                    status=result.get("status", 500)
                )
            
            return json_response({
                "success": True,
                "organization_id": int(org_id),
                "data": result.get("data", [])
            })
        
        # Check if requesting projects for organization
        if path.endswith("/projects"):
            # Projects can be fetched with organization filter
            page, per_page = parse_pagination_params(query_params)
            
            result = await client.get_projects(page=page, per_page=per_page)
            
            if result.get("error"):
                return error_response(
                    result.get("message", "Failed to fetch organization projects"),
                    status=result.get("status", 500)
                )
            
            data = result.get("data", {})
            
            # Filter projects by organization if we have the data
            if isinstance(data, dict) and "projects" in data:
                projects = [
                    p for p in data.get("projects", [])
                    if str(p.get("organization")) == org_id
                ]
                return json_response({
                    "success": True,
                    "organization_id": int(org_id),
                    "data": projects,
                    "count": len(projects)
                })
            
            return json_response({
                "success": True,
                "organization_id": int(org_id),
                "data": data
            })
        
        # Get organization details
        result = await client.get_organization(int(org_id))
        
        if result.get("error"):
            return error_response(
                result.get("message", "Organization not found"),
                status=result.get("status", 404)
            )
        
        return json_response({
            "success": True,
            "data": result.get("data")
        })
    
    # List organizations with pagination
    page, per_page = parse_pagination_params(query_params)
    search = query_params.get("search", query_params.get("q"))
    
    result = await client.get_organizations(page=page, per_page=per_page, search=search)
    
    if result.get("error"):
        return error_response(
            result.get("message", "Failed to fetch organizations"),
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
