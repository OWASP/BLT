"""Route discovery metadata for BLT-API.

Keep this close to route registration: when `src/main.py` registers or changes a
route, update the matching metadata here so `/routes` stays useful for humans,
contributors, and coding agents.
"""

from copy import deepcopy
from typing import Any, Dict, List, Tuple


RouteMetadata = Dict[str, Any]
RouteKey = Tuple[str, str]


def _param(name: str, type_: str = "string", required: bool = False, description: str = "") -> Dict[str, Any]:
    data = {"name": name, "type": type_, "required": required}
    if description:
        data["description"] = description
    return data


ID_PATH = [_param("id", "integer", True, "Route resource identifier.")]
PAGINATION = [
    _param("page", "integer", False, "Page number, defaults to 1."),
    _param("per_page", "integer", False, "Items per page, defaults to 20."),
]


def _meta(
    summary: str,
    auth_type: str = "api_key",
    path_params: List[Dict[str, Any]] | None = None,
    query_params: List[Dict[str, Any]] | None = None,
    body_fields: List[Dict[str, Any]] | None = None,
) -> RouteMetadata:
    return {
        "summary": summary,
        "auth_type": auth_type,
        "path_params": path_params or [],
        "query_params": query_params or [],
        "body_fields": body_fields or [],
    }


ROUTE_METADATA: Dict[RouteKey, RouteMetadata] = {
    # Browser/static/public utility routes
    ("GET", "/"): _meta("Serve the public BLT-API landing page.", "public"),
    ("GET", "/blt-api.png"): _meta("Serve the BLT API logo asset.", "public"),
    ("GET", "/dashboard"): _meta("Serve the interactive BLT API explorer and documentation UI.", "public"),
    ("GET", "/auth"): _meta("Serve the legacy browser auth/dashboard entry page.", "public"),
    ("GET", "/health"): _meta("Return API health status.", "public"),
    ("GET", "/routes"): _meta("List registered API routes with discovery metadata."),

    # Bugs
    ("GET", "/bugs/search"): _meta(
        "Search bugs by URL or description text.",
        query_params=[
            _param("q", "string", True, "Search query."),
            _param("limit", "integer", False, "Maximum results, defaults to 10."),
        ],
    ),
    ("GET", "/bugs"): _meta(
        "List bugs with pagination and optional filters.",
        query_params=PAGINATION + [
            _param("status", "string", False, "Bug status filter."),
            _param("domain", "integer", False, "Domain id filter."),
            _param("verified", "boolean", False, "Verification status filter."),
        ],
    ),
    ("POST", "/bugs"): _meta(
        "Create a bug report.",
        body_fields=[
            _param("url", "string", True, "Affected URL."),
            _param("description", "string", True, "Bug description."),
            _param("markdown_description", "string", False),
            _param("domain", "integer", False),
            _param("screenshot", "string", False),
        ],
    ),
    ("PATCH", "/bugs/{id}"): _meta(
        "Update a bug owned by the authenticated user.",
        auth_type="api_key_and_bearer_jwt",
        path_params=ID_PATH,
        body_fields=[
            _param("status", "string", False),
            _param("verified", "boolean", False),
            _param("score", "integer", False),
            _param("description", "string", False),
            _param("github_url", "string", False),
        ],
    ),
    ("GET", "/bugs/{id}"): _meta("Get detailed bug information.", path_params=ID_PATH),

    # Users
    ("GET", "/users"): _meta("List users with pagination.", query_params=PAGINATION),
    ("POST", "/users"): _meta(
        "Create a user account.",
        body_fields=[
            _param("username", "string", True),
            _param("email", "string", True),
            _param("password", "string", True),
            _param("description", "string", False),
        ],
    ),
    ("GET", "/users/{id}"): _meta("Get a user by id.", path_params=ID_PATH),
    ("GET", "/users/{id}/profile"): _meta("Get public profile data for a user.", path_params=ID_PATH),
    ("GET", "/users/{id}/bugs"): _meta("List bugs reported by a user.", path_params=ID_PATH, query_params=PAGINATION),
    ("GET", "/users/{id}/domains"): _meta("List domains associated with a user.", path_params=ID_PATH, query_params=PAGINATION),
    ("GET", "/users/{id}/followers"): _meta("List users following a user.", path_params=ID_PATH, query_params=PAGINATION),
    ("GET", "/users/{id}/following"): _meta("List users followed by a user.", path_params=ID_PATH, query_params=PAGINATION),

    # Auth: canonical /api/auth namespace
    ("POST", "/api/auth/signup"): _meta(
        "Register a new local account.",
        auth_type="public",
        body_fields=[
            _param("username", "string", True),
            _param("email", "string", True),
            _param("password", "string", True),
            _param("redirect_uri", "string", False),
        ],
    ),
    ("POST", "/api/auth/signin"): _meta(
        "Sign in and receive a Bearer JWT session token.",
        auth_type="public",
        body_fields=[
            _param("identifier", "string", True, "Username or email."),
            _param("username", "string", False),
            _param("email", "string", False),
            _param("password", "string", True),
            _param("redirect_uri", "string", False),
        ],
    ),
    ("GET", "/api/auth/verify-email"): _meta(
        "Verify an email address using a verification token.",
        auth_type="public",
        query_params=[_param("token", "string", True)],
    ),
    ("POST", "/api/auth/verify-local"): _meta(
        "Verify a localhost development account using a console OTP.",
        auth_type="public",
        body_fields=[
            _param("identifier", "string", True),
            _param("dev_otp", "string", True),
        ],
    ),
    ("GET", "/api/auth/api-keys"): _meta("List user-owned API keys.", "bearer_jwt"),
    ("POST", "/api/auth/api-keys"): _meta(
        "Create a user-owned API key.",
        "bearer_jwt",
        body_fields=[
            _param("name", "string", True),
            _param("scopes", "array", False),
        ],
    ),
    ("DELETE", "/api/auth/api-keys/{id}"): _meta("Revoke a user-owned API key.", "bearer_jwt", path_params=ID_PATH),

    # Domains
    ("GET", "/domains"): _meta("List domains with pagination.", query_params=PAGINATION),
    ("GET", "/domains/{id}"): _meta("Get a domain by id.", path_params=ID_PATH),
    ("GET", "/domains/{id}/tags"): _meta("List tags associated with a domain.", path_params=ID_PATH, query_params=PAGINATION),

    # Organizations
    ("GET", "/organizations"): _meta(
        "List organizations with pagination and filters.",
        query_params=PAGINATION + [
            _param("search", "string", False),
            _param("q", "string", False),
            _param("type", "string", False),
            _param("is_active", "boolean", False),
        ],
    ),
    ("GET", "/organizations/{id}"): _meta(
        "Get an organization by id.",
        path_params=ID_PATH,
        query_params=[_param("include", "string", False, "Comma-separated related data to include.")],
    ),
    ("GET", "/organizations/{id}/domains"): _meta("List domains for an organization.", path_params=ID_PATH, query_params=PAGINATION),
    ("GET", "/organizations/{id}/bugs"): _meta("List bugs for an organization's domains.", path_params=ID_PATH, query_params=PAGINATION),
    ("GET", "/organizations/{id}/managers"): _meta("List organization managers.", path_params=ID_PATH),
    ("GET", "/organizations/{id}/tags"): _meta("List organization tags.", path_params=ID_PATH),
    ("GET", "/organizations/{id}/integrations"): _meta("List organization integrations.", path_params=ID_PATH),
    ("GET", "/organizations/{id}/stats"): _meta("Get organization statistics.", path_params=ID_PATH),

    # Projects
    ("GET", "/projects"): _meta("List projects with pagination.", query_params=PAGINATION),
    ("GET", "/projects/{id}"): _meta("Get a project by id.", path_params=ID_PATH),
    ("GET", "/projects/{id}/contributors"): _meta("List project contributors.", path_params=ID_PATH, query_params=PAGINATION),

    # Bug hunts
    ("GET", "/hunts/active"): _meta("List active bug hunts."),
    ("GET", "/hunts/previous"): _meta("List previous bug hunts."),
    ("GET", "/hunts/upcoming"): _meta("List upcoming bug hunts."),
    ("GET", "/hunts"): _meta("List bug hunts."),
    ("GET", "/hunts/{id}"): _meta("Get a bug hunt by id.", path_params=ID_PATH),

    # Stats and rankings
    ("GET", "/stats"): _meta("Get platform statistics."),
    ("GET", "/leaderboard"): _meta("List leaderboard entries.", query_params=PAGINATION),
    ("GET", "/leaderboard/monthly"): _meta(
        "List monthly leaderboard entries.",
        query_params=PAGINATION + [_param("month", "integer", False), _param("year", "integer", False)],
    ),
    ("GET", "/leaderboard/organizations"): _meta("List organization leaderboard entries.", query_params=PAGINATION),

    # Misc resources
    ("GET", "/contributors"): _meta("List contributors.", query_params=PAGINATION),
    ("GET", "/contributors/{id}"): _meta("Get a contributor by id.", path_params=ID_PATH),
    ("GET", "/repos"): _meta("List repositories.", query_params=PAGINATION),
    ("GET", "/repos/{id}"): _meta("Get a repository by id.", path_params=ID_PATH),
}

# Legacy /auth/* JSON routes mirror the canonical /api/auth/* metadata.
for _method, _api_path in [
    ("POST", "/api/auth/signup"),
    ("POST", "/api/auth/signin"),
    ("GET", "/api/auth/verify-email"),
    ("POST", "/api/auth/verify-local"),
    ("GET", "/api/auth/api-keys"),
    ("POST", "/api/auth/api-keys"),
    ("DELETE", "/api/auth/api-keys/{id}"),
]:
    ROUTE_METADATA[(_method, _api_path.replace("/api/auth", "/auth", 1))] = deepcopy(ROUTE_METADATA[(_method, _api_path)])


def _default_metadata(method: str, path: str) -> RouteMetadata:
    return _meta(f"{method.upper()} {path} endpoint.")


def _unversioned_path(path: str) -> str:
    if path == "/v2":
        return "/"
    if path.startswith("/v2/"):
        return path[3:]
    return path


def metadata_for(method: str, path: str) -> RouteMetadata:
    """Return route metadata for an exact or /v2-prefixed route."""
    method = method.upper()
    metadata = ROUTE_METADATA.get((method, path))
    if metadata is None and path.startswith("/v2"):
        metadata = ROUTE_METADATA.get((method, _unversioned_path(path)))
    if metadata is None:
        metadata = _default_metadata(method, path)
    return deepcopy(metadata)
