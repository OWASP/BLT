"""
Tests for BLT API landing page and dashboard handlers.
"""

import importlib
import sys
import types
from pathlib import Path

import pytest

# Add src to path for imports to work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from handlers.homepage import handle_blt_api_logo, handle_dashboard, handle_homepage


class MockRequest:
    """Mock request object for testing."""

    def __init__(self, url="https://blt-api.workers.dev/"):
        self.url = url
        self.method = "GET"


class MockEnv:
    """Mock environment object for testing."""
    pass


async def _body(handler, url="https://blt-api.workers.dev/", path="/"):
    response = await handler(
        MockRequest(url=url),
        MockEnv(),
        path_params={},
        query_params={},
        path=path,
    )
    assert response is not None
    assert hasattr(response, "body")
    assert "text/html" in response.headers["Content-Type"]
    return response.body


class TestHomepageHandler:
    """Tests for the public BLT API landing page."""

    @pytest.mark.asyncio
    async def test_homepage_returns_landing_page_html(self):
        content = await _body(handle_homepage)

        assert "<!doctype html>" in content.lower()
        assert "BLT API" in content
        assert "Build with" in content
        assert "Everything you need to test a route" in content
        assert "The dashboard keeps route docs" in content
        assert 'src="/blt-api.png"' in content
        assert 'src="/blt-api.svg"' not in content

    @pytest.mark.asyncio
    async def test_homepage_links_to_dashboard_route_not_html_or_v2_page(self):
        content = await _body(handle_homepage, url="https://custom-api.example.com/")

        assert "https://custom-api.example.com/dashboard" in content
        assert "/dashboard.html" not in content
        assert "/v2/dashboard" not in content
        assert "Open v2 docs" not in content

    @pytest.mark.asyncio
    async def test_homepage_points_protected_endpoint_cards_to_dashboard(self):
        content = await _body(handle_homepage)

        assert "Cards point to the dashboard" in content
        for label in ["/bugs", "/users", "/domains", "/organizations", "/projects", "/stats"]:
            assert label in content
        assert "X-BLT-API-Key" in content

    @pytest.mark.asyncio
    async def test_blt_api_logo_asset_is_served(self):
        response = await handle_blt_api_logo(
            MockRequest(url="https://blt-api.workers.dev/blt-api.png"),
            MockEnv(),
            path_params={},
            query_params={},
            path="/blt-api.png",
        )

        assert response.status == 200
        assert response.headers["Content-Type"] == "image/webp"
        assert isinstance(response.body, bytes)
        assert response.body.startswith(b"RIFF")


class TestDashboardHandler:
    """Tests for the interactive API dashboard/docs page."""

    @pytest.mark.asyncio
    async def test_dashboard_returns_html(self):
        content = await _body(
            handle_dashboard,
            url="https://blt-api.workers.dev/dashboard",
            path="/dashboard",
        )

        assert "<!doctype html>" in content.lower()
        assert "BLT API" in content
        assert "Try It" in content

    @pytest.mark.asyncio
    async def test_dashboard_contains_route_catalog(self):
        content = await _body(handle_dashboard, url="https://api.example.com/dashboard", path="/dashboard")

        for route in [
            "/v2/auth/signup",
            "/v2/auth/signin",
            "/v2/auth/verify-email",
            "/v2/bugs",
            "/v2/users",
            "/v2/domains",
            "/v2/organizations",
            "/v2/jobs",
            "/v2/jobs/{id}/view",
            "/v2/hackathons",
            "/v2/hackathons/{id}/register",
        ]:
            assert route in content

    @pytest.mark.asyncio
    async def test_dashboard_contains_try_it_console(self):
        content = await _body(handle_dashboard, url="https://api.example.com/dashboard", path="/dashboard")

        assert "sendRequestButton" in content
        assert "async function sendRequest" in content
        assert "fetch(request.url, fetchOptions)" in content
        assert "function shouldUseDemoResponse" in content
        assert "function buildDemoResponse" in content
        assert "responseBody" in content
        assert "copyCurlButton" not in content
        assert "curlOutput" not in content
        assert "Generated cURL" not in content

    @pytest.mark.asyncio
    async def test_dashboard_signed_out_try_it_uses_demo_without_fetching(self):
        content = await _body(handle_dashboard, url="https://api.example.com/dashboard", path="/dashboard")

        send_start = content.index("async function sendRequest()")
        send_end = content.index("function extractUsername", send_start)
        send_body = content[send_start:send_end]

        assert "if (shouldUseDemoResponse(activeRoute))" in send_body
        assert "await simulateDemoResponse(activeRoute, start);" in send_body
        assert send_body.index("await simulateDemoResponse(activeRoute, start);") < send_body.index("fetch(request.url, fetchOptions)")
        assert "Demo response. Sign in and create an API key to send live requests." in content

    @pytest.mark.asyncio
    async def test_dashboard_contains_api_key_panel(self):
        content = await _body(handle_dashboard, url="https://api.example.com/dashboard", path="/dashboard")

        assert "profileModal" in content
        assert "accountOpenButton" in content
        assert "createApiKeyButton" in content
        assert "apiKeyList" in content
        assert "X-BLT-API-Key" in content
        assert "blt-dashboard-api-key" in content
        assert 'src="/blt-api.png"' in content
        assert 'src="/blt-api.svg"' not in content

    @pytest.mark.asyncio
    async def test_dashboard_profile_modal_omits_manual_api_key_controls(self):
        content = await _body(handle_dashboard, url="https://api.example.com/dashboard", path="/dashboard")

        assert "Active API key" not in content
        assert "savedKeyDisplay" not in content
        assert "copyApiKeyButton" not in content
        assert "clearApiKeyButton" not in content
        assert "Paste existing key" not in content
        assert "apiKeyInput" not in content
        assert "saveApiKeyButton" not in content

    @pytest.mark.asyncio
    async def test_dashboard_signup_verification_is_backend_driven(self):
        content = await _body(handle_dashboard, url="https://api.example.com/dashboard", path="/dashboard")

        assert "if (data.requires_local_verification)" in content
        assert "isLocalDevelopment" not in content

    @pytest.mark.asyncio
    async def test_dashboard_signout_clears_saved_api_key(self):
        content = await _body(handle_dashboard, url="https://api.example.com/dashboard", path="/dashboard")

        signout_start = content.index("function signOutAccount()")
        signout_end = content.index("function updateApiKeyStatus()", signout_start)
        signout_body = content[signout_start:signout_end]

        assert "clearSession();" in signout_body
        assert "localStorage.removeItem(API_KEY_STORAGE_KEY);" in signout_body
        assert "closeProfileModal();" in signout_body

    @pytest.mark.asyncio
    async def test_dashboard_uses_safe_response_rendering(self):
        content = await _body(handle_dashboard, url="https://api.example.com/dashboard", path="/dashboard")

        assert "elements.responseBody.textContent = displayText" in content
        assert "elements.responseBody.textContent = lastResponseText" in content
        assert "JSON.stringify(value, null, 2)" in content
        assert "responseBody.innerHTML" not in content

    @pytest.mark.asyncio
    async def test_dashboard_replaces_origin_without_v2_page_prefix(self):
        content = await _body(
            handle_dashboard,
            url="https://custom-api.example.com/dashboard",
            path="/dashboard",
        )

        assert 'const baseUrl = "https://custom-api.example.com";' in content
        assert "https://custom-api.example.com/v2/dashboard" not in content
        assert "https://custom-api.example.com/dashboard.html" not in content

    def test_dashboard_route_registration_uses_plain_dashboard_only(self, monkeypatch):
        previous_workers = sys.modules.get("workers")
        workers_mod = types.ModuleType("workers")

        class WorkerEntrypoint:
            pass

        setattr(workers_mod, "WorkerEntrypoint", WorkerEntrypoint)
        with monkeypatch.context() as patch_context:
            patch_context.setitem(sys.modules, "workers", workers_mod)
            main = importlib.reload(sys.modules["main"]) if "main" in sys.modules else importlib.import_module("main")

            route_paths = {(route.method, route.pattern) for route in main.router.routes}
            assert ("GET", "/dashboard") in route_paths
            assert ("GET", "/blt-api.png") in route_paths
            assert ("GET", "/dashboard.html") not in route_paths
            assert ("GET", "/v2/dashboard") not in route_paths
            assert ("GET", "/v2/dashboard.html") not in route_paths
            assert ("GET", "/v2") not in route_paths

        assert sys.modules.get("workers") is previous_workers

    def test_new_user_owned_api_routes_are_registered_for_discovery(self, monkeypatch):
        previous_workers = sys.modules.get("workers")
        workers_mod = types.ModuleType("workers")

        class WorkerEntrypoint:
            pass

        setattr(workers_mod, "WorkerEntrypoint", WorkerEntrypoint)
        with monkeypatch.context() as patch_context:
            patch_context.setitem(sys.modules, "workers", workers_mod)
            main = importlib.reload(sys.modules["main"]) if "main" in sys.modules else importlib.import_module("main")

            route_paths = {(route.method, route.pattern) for route in main.router.routes}
            for route in [
                ("GET", "/v2/jobs"),
                ("POST", "/v2/jobs"),
                ("GET", "/v2/jobs/{id}"),
                ("PATCH", "/v2/jobs/{id}"),
                ("POST", "/v2/jobs/{id}/view"),
                ("GET", "/v2/jobs/stats"),
                ("GET", "/v2/hackathons"),
                ("POST", "/v2/hackathons"),
                ("GET", "/v2/hackathons/{slug}"),
                ("PATCH", "/v2/hackathons/{id}"),
                ("POST", "/v2/hackathons/{id}/register"),
            ]:
                assert route in route_paths

        assert sys.modules.get("workers") is previous_workers
