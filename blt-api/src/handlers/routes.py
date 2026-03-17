"""
Routes handler for the BLT API.

Exposes registered API routes for programmatic discoverability.
"""

from typing import Any, Dict
from workers import Response


async def handle_routes(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle route discovery requests.

    Endpoints:
        GET /routes - List all registered API routes
    """
    from main import router

    routes = router.get_route_list()

    return Response.json({
        "success": True,
        "data": routes,
        "count": len(routes)
    })
