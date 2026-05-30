"""Legacy browser auth route handler."""

from typing import Any, Dict

from .homepage import handle_homepage


async def handle_auth_page(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str,
) -> Any:
    """Serve the homepage modal experience for backward-compatible /auth links."""
    return await handle_homepage(request, env, path_params, query_params, path)
