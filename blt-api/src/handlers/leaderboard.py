"""
Leaderboard handler for the BLT API.
"""

from typing import Any, Dict
from ..utils import json_response, error_response, paginated_response, parse_pagination_params
from ..client import create_client


async def handle_leaderboard(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle leaderboard-related requests.
    
    Endpoints:
        GET /leaderboard - Get global leaderboard
        GET /leaderboard/monthly - Get monthly leaderboard
        GET /leaderboard/organizations - Get organization leaderboard
    """
    client = create_client(env)
    page, per_page = parse_pagination_params(query_params)
    
    # Monthly leaderboard
    if path.endswith("/monthly"):
        month = query_params.get("month")
        year = query_params.get("year")
        
        # Validate month and year if provided
        if month:
            try:
                month_int = int(month)
                if month_int < 1 or month_int > 12:
                    return error_response("Month must be between 1 and 12", status=400)
            except ValueError:
                return error_response("Invalid month format", status=400)
        else:
            month_int = None
        
        if year:
            try:
                year_int = int(year)
                if year_int < 2000 or year_int > 2100:
                    return error_response("Invalid year", status=400)
            except ValueError:
                return error_response("Invalid year format", status=400)
        else:
            year_int = None
        
        result = await client.get_leaderboard(
            page=page,
            per_page=per_page,
            month=month_int,
            year=year_int
        )
        
        if result.get("error"):
            return error_response(
                result.get("message", "Failed to fetch monthly leaderboard"),
                status=result.get("status", 500)
            )
        
        data = result.get("data", {})
        
        return json_response({
            "success": True,
            "type": "monthly",
            "month": month_int,
            "year": year_int,
            "data": data.get("results", data) if isinstance(data, dict) else data,
            "pagination": {
                "page": page,
                "per_page": per_page
            }
        })
    
    # Organization leaderboard
    if path.endswith("/organizations"):
        result = await client.get_leaderboard(
            page=page,
            per_page=per_page,
            leaderboard_type="organizations"
        )
        
        if result.get("error"):
            return error_response(
                result.get("message", "Failed to fetch organization leaderboard"),
                status=result.get("status", 500)
            )
        
        data = result.get("data", {})
        
        # Handle paginated response
        if isinstance(data, dict) and "results" in data:
            return json_response({
                "success": True,
                "type": "organizations",
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
            "type": "organizations",
            "data": data
        })
    
    # Global leaderboard
    result = await client.get_leaderboard(page=page, per_page=per_page)
    
    if result.get("error"):
        return error_response(
            result.get("message", "Failed to fetch leaderboard"),
            status=result.get("status", 500)
        )
    
    data = result.get("data", {})
    
    # Handle paginated response
    if isinstance(data, dict) and "results" in data:
        return json_response({
            "success": True,
            "type": "global",
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
        return json_response({
            "success": True,
            "type": "global",
            "data": data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "count": len(data)
            }
        })
    
    return json_response({
        "success": True,
        "type": "global",
        "data": data
    })
