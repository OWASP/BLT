"""
Routes handler for the BLT API.

Exposes registered API routes for programmatic discoverability.
"""

from typing import Any, Dict, Callable
from workers import Response
from router import Router


def make_routes_handler(router: Router) -> Callable:
    """
    Create a routes handler with access to the router instance.
    
    This factory pattern avoids circular imports by accepting the router
    as a parameter rather than importing it from main.
    
    Args:
        router: The Router instance to query for registered routes
    
    Returns:
        An async handler function for the /routes endpoint
    """
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
        routes = router.get_route_list()

        return Response.json({
            "success": True,
            "data": routes,
            "count": len(routes)
        })
    
    return handle_routes
