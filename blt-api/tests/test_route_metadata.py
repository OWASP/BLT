"""Tests for expanded route discovery metadata."""

import importlib
import sys
import types


REQUIRED_METADATA_KEYS = {"summary", "auth_type", "path_params", "query_params", "body_fields"}
VALID_AUTH_TYPES = {"public", "api_key", "bearer_jwt", "api_key_and_bearer_jwt"}


def _load_main_with_workers():
    workers_mod = types.ModuleType("workers")

    class WorkerEntrypoint:
        pass

    class Response:
        @staticmethod
        def json(data, status=200, headers=None):
            return {"status": status, "headers": headers or {}, "data": data}

        @staticmethod
        def new(body=None, status=200, headers=None):
            return {"status": status, "headers": headers or {}, "body": body}

    setattr(workers_mod, "WorkerEntrypoint", WorkerEntrypoint)
    setattr(workers_mod, "Response", Response)
    previous_workers = sys.modules.get("workers")
    sys.modules["workers"] = workers_mod
    try:
        return importlib.reload(sys.modules["main"]) if "main" in sys.modules else importlib.import_module("main")
    finally:
        if previous_workers is None:
            sys.modules.pop("workers", None)
        else:
            sys.modules["workers"] = previous_workers


def _routes_by_key():
    main = _load_main_with_workers()
    return {(route["method"], route["path"]): route for route in main.router.get_route_list()}


def _names(items):
    return {item["name"] for item in items}


def test_all_registered_routes_preserve_method_path_and_include_metadata():
    routes = _routes_by_key()

    assert routes
    for route in routes.values():
        assert route["method"]
        assert route["path"].startswith("/")
        assert REQUIRED_METADATA_KEYS <= set(route)
        assert route["summary"]
        assert route["auth_type"] in VALID_AUTH_TYPES
        assert isinstance(route["path_params"], list)
        assert isinstance(route["query_params"], list)
        assert isinstance(route["body_fields"], list)


def test_bug_routes_include_useful_metadata_for_agents():
    routes = _routes_by_key()
    list_route = routes[("GET", "/bugs")]
    detail_route = routes[("GET", "/bugs/{id}")]
    create_route = routes[("POST", "/bugs")]

    assert list_route["auth_type"] == "api_key"
    assert {"page", "per_page", "status", "domain", "verified"} <= _names(list_route["query_params"])
    assert "id" in _names(detail_route["path_params"])
    assert {"url", "description"} <= _names(create_route["body_fields"])


def test_auth_routes_separate_public_login_from_bearer_api_key_management():
    routes = _routes_by_key()
    signin = routes[("POST", "/api/auth/signin")]
    create_key = routes[("POST", "/api/auth/api-keys")]
    delete_key = routes[("DELETE", "/api/auth/api-keys/{id}")]

    assert signin["auth_type"] == "public"
    assert {"identifier", "password"} <= _names(signin["body_fields"])
    assert create_key["auth_type"] == "bearer_jwt"
    assert {"name", "scopes"} <= _names(create_key["body_fields"])
    assert "id" in _names(delete_key["path_params"])


def test_v2_routes_include_expanded_metadata_too():
    routes = _routes_by_key()
    bugs = routes[("GET", "/v2/bugs")]
    api_keys = routes[("GET", "/v2/auth/api-keys")]
    route_discovery = routes[("GET", "/v2/routes")]

    assert bugs["auth_type"] == "api_key"
    assert {"page", "per_page"} <= _names(bugs["query_params"])
    assert api_keys["auth_type"] == "bearer_jwt"
    assert route_discovery["auth_type"] == "api_key"
    assert route_discovery["summary"].lower().startswith("list registered")


def test_public_routes_are_marked_public():
    routes = _routes_by_key()

    for key in [("GET", "/"), ("GET", "/health"), ("POST", "/api/auth/signup")]:
        assert routes[key]["auth_type"] == "public"


def test_protected_user_creation_route_keeps_api_key_gate_metadata():
    routes = _routes_by_key()

    assert routes[("POST", "/users")]["auth_type"] == "api_key"
    assert {"username", "email", "password"} <= _names(routes[("POST", "/users")]["body_fields"])
