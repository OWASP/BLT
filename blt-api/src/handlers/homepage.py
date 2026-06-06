"""
Static page handlers for the BLT API landing page and dashboard.
"""

from pathlib import Path
from typing import Any, Dict

try:
    from js import Response, Headers
    _WORKERS_RUNTIME = True
except ImportError:
    _WORKERS_RUNTIME = False
    from utils import Response, Headers


def _api_base_url(request: Any) -> str:
    """Build the origin base URL used by static pages for API links."""
    url = str(request.url)
    if "://" not in url:
        return "https://blt-api.workers.dev"

    scheme, rest = url.split("://", 1)
    host = rest.split("/", 1)[0]
    return f"{scheme}://{host}"


def _serve_page(request: Any, page_name: str) -> Any:
    """Read a static page, replace API placeholders, and return an HTML response."""
    html_file = Path(__file__).resolve().parent.parent / "pages" / page_name
    html_content = html_file.read_text(encoding="utf-8").replace(
        "[[API_BASE_URL]]",
        _api_base_url(request),
    )

    headers = {
        "Content-Type": "text/html; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-BLT-API-Key",
    }

    if _WORKERS_RUNTIME:
        # Cloudflare Workers expects Headers.new(...) input to be a Sequence.
        js_headers = Headers.new(list(headers.items()))
        return Response.new(html_content, status=200, headers=js_headers)

    return Response.new(
        html_content,
        {
            "status": 200,
            "headers": headers,
        },
    )


def _serve_static_file(file_name: str, content_type: str) -> Any:
    """Serve a small static asset through the Worker routing path."""
    asset_file = Path(__file__).resolve().parents[2] / "static" / file_name
    asset_content = asset_file.read_bytes()
    headers = {
        "Content-Type": content_type,
        "Cache-Control": "public, max-age=86400",
        "Access-Control-Allow-Origin": "*",
    }

    if _WORKERS_RUNTIME:
        js_headers = Headers.new(list(headers.items()))
        return Response.new(asset_content, status=200, headers=js_headers)

    return Response.new(
        asset_content,
        {
            "status": 200,
            "headers": headers,
        },
    )


async def handle_homepage(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str,
) -> Any:
    """Handle BLT API landing page endpoint (GET /)."""
    return _serve_page(request, "index.html")


async def handle_dashboard(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str,
) -> Any:
    """Handle BLT API dashboard/docs endpoint (GET /dashboard)."""
    return _serve_page(request, "dashboard.html")


async def handle_blt_api_logo(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str,
) -> Any:
    """Serve the BLT API logo when static asset passthrough is unavailable."""
    return _serve_static_file("blt-api.png", "image/webp")
