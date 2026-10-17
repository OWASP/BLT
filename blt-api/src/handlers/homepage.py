"""
Static browser/page handlers for BLT-API.

Route map:
- GET / -> src/pages/index.html
- GET /dashboard -> src/pages/dashboard.html
- GET /blt-api.png -> static/blt-api.png
"""

from pathlib import Path
from typing import Any, Dict

try:
    from js import Response, Headers # pyright: ignore[reportMissingImports]
    _WORKERS_RUNTIME = True
except ImportError:
    _WORKERS_RUNTIME = False
    from utils import Response, Headers


LLM_TXT_CONTENT = """
# BLT-API agent context

BLT-API is the Python Cloudflare Workers REST API for OWASP BLT (Bug Logging Tool). It exposes BLT resources such as bugs, users, domains, organizations, projects, hunts, stats, leaderboard, contributors, repositories, auth, and route discovery.

Use this web route as a compact map before editing the repo. It is intentionally short and secret-free.

## Stack

- Runtime: Cloudflare Workers Python runtime (`compatibility_flags = ["python_workers"]`).
- Worker entrypoint: `src/main.py`, `Default(WorkerEntrypoint)`.
- Router: `src/router.py` with route registration in `src/main.py`.
- Database: Cloudflare D1 SQLite, binding name `blt_api` in `wrangler.toml`.
- Package/dev tools: Python 3.12+, `uv`, Wrangler, workers-py.
- Static pages: `src/pages/index.html` and `src/pages/dashboard.html`.

## Local development flow

```bash
uv sync
uv tool install workers-py
bash scripts/setup_local_db.sh
wrangler dev --port 8787
```

Useful local URLs:
- Landing page: `http://localhost:8787`
- API dashboard: `http://localhost:8787/dashboard`
- Route discovery: `http://localhost:8787/routes` and `/v2/routes`

Run tests with:

```bash
uv run pytest
```

When using a temporary runner, include needed test dependencies such as `pytest`, `pytest-asyncio`, and `requests`.

## File map

- `src/main.py`: imports handlers, registers unversioned and `/v2` routes, handles CORS preflight and API-key validation before dispatch.
- `src/router.py`: path matching, path/query parsing, and `get_route_list()` for `/routes`.
- `src/handlers/`: endpoint handlers. Each handler receives `request`, `env`, `path_params`, `query_params`, and `path`.
- `src/handlers/routes.py`: `/routes` response factory using the live router.
- `src/libs/api_key.py`: shared and user API key validation for the `X-BLT-API-Key` API access gate.
- `src/libs/jwt_utils.py`: JWT encode/decode helpers for Bearer user identity.
- `src/libs/auth_context.py`: authenticated user context helpers.
- `src/libs/db.py`: D1 database binding discovery and safety helpers.
- `migrations/`: D1 schema migrations.
- `scripts/`: setup, migration, and environment-loading helpers.
- `tests/`: unit/regression tests for handlers, router, auth, API keys, pages, and main worker routing.
- `docs/DATABASE.md`: D1 schema and database workflow details.

## Auth model

Keep these concepts separate:

- `X-BLT-API-Key` is the API access gate for protected API requests. It is checked before route dispatch in `src/main.py` through `src/libs/api_key.py`.
- JWT/Bearer tokens represent user identity and user session state after signin. They are used by account-level flows such as listing, creating, and revoking user API keys.
- Public routes and auth bootstrap routes are allowlisted in `src/libs/api_key.py`.
- Do not change API-key enforcement while only updating docs or agent guidance.

## Route direction

- Existing unversioned routes remain for backward compatibility.
- `/v2` routes are registered in `src/main.py` with `_add_v2_route(...)` and should be preferred by new API consumers where available.
- Authentication APIs also have legacy `/auth/*` and `/v2/auth/*` paths, while README documents `/api/auth/*` as the canonical auth namespace.
- When adding or changing routes, update tests and any route discovery metadata in the same change.

## D1 and deployment notes

- Wrangler config lives in `wrangler.toml`.
- D1 migrations live in `migrations/` and are applied with Wrangler.
- Local DB setup is automated by `scripts/setup_local_db.sh`.
- Deployment runs through Wrangler; the build command in `wrangler.toml` runs `scripts/migrate.sh`.
- Configure production secrets with Wrangler secret commands or approved environment tooling. Never commit real secrets.

## Agent guardrails

- Read `README.md` for the human overview and `CONTRIBUTING.md` for contributor setup.
- Keep README changes human-readable, short, and polished; put agent-specific guidance here or in `AGENTS.md` if added later.
- Prefer minimal, tested changes. Add or update tests for behavior changes.
- Avoid anonymous-report scope unless an issue explicitly asks for it.
- Do not conflate the shared API gate with JWT identity.
- Keep comments short and useful; avoid noisy context dumps.
""".lstrip()


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


def _serve_text(content: str) -> Any:
    """Serve text content through the Worker routing path."""
    headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "public, max-age=300",
        "Access-Control-Allow-Origin": "*",
    }

    if _WORKERS_RUNTIME:
        js_headers = Headers.new(list(headers.items()))
        return Response.new(content, status=200, headers=js_headers)

    return Response.new(
        content,
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
    return _serve_static_file("blt-api.png", "image/png")


async def handle_llm_txt(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str,
) -> Any:
    """Serve the compact BLT-API agent context at GET /llm.txt."""
    return _serve_text(LLM_TXT_CONTENT)
