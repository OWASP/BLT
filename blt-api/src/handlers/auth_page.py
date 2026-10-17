"""
Legacy browser /auth route.

This is not a JSON auth API endpoint. It serves the dashboard/docs UI for
older browser and email links; JSON auth APIs live under /api/auth/* plus
legacy compatibility namespaces.
"""

from typing import Any, Dict

from .homepage import handle_dashboard


async def handle_auth_page(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str,
) -> Any:
    """Serve the dashboard/docs experience for backward-compatible /auth links."""
    return await handle_dashboard(request, env, path_params, query_params, path)
