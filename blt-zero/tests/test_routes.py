import json
import sys
import types
import unittest
from pathlib import Path
from urllib.parse import urlparse


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))


class FakeResponse:
    def __init__(self, body="", status=200, headers=None):
        self.body = body
        self.status = status
        self.headers = headers or {}

    @staticmethod
    def json(data, status=200, headers=None):
        response_headers = {"content-type": "application/json"}
        if headers:
            response_headers.update(headers)
        return FakeResponse(json.dumps(data), status=status, headers=response_headers)


class FakeWorkerEntrypoint:
    pass


class FakeHeaders:
    @staticmethod
    def new():
        return {}


async def fake_fetch(*_args, **_kwargs):
    return FakeResponse(status=202)


class FakeURL:
    @staticmethod
    def new(raw_url):
        parsed = urlparse(raw_url)
        return types.SimpleNamespace(pathname=parsed.path or "/")


sys.modules["workers"] = types.SimpleNamespace(
    WorkerEntrypoint=FakeWorkerEntrypoint,
    Response=FakeResponse,
)
sys.modules["js"] = types.SimpleNamespace(
    URL=FakeURL,
    Headers=FakeHeaders,
    fetch=fake_fetch,
)

from main import Default  # noqa: E402


class Env:
    APP_ORIGIN = "https://zero.example.test"
    ZIP_MAX_FILES = "5"
    ZIP_MAX_TOTAL_BYTES = "5242880"


class Request:
    def __init__(self, method, path):
        self.method = method
        self.url = f"https://zero.example.test{path}"
        self.headers = {}


class RouteTests(unittest.IsolatedAsyncioTestCase):
    async def fetch(self, method, path):
        app = Default()
        app.env = Env()
        return await app.fetch(Request(method, path))

    async def test_linked_pages_render_instead_of_404(self):
        cases = [
            ("/docs/security", "Security Model"),
            ("/docs/org-onboarding", "Organization Onboarding"),
            ("/docs/decrypt", "Decrypt Guide"),
            ("/admin/onboard", "Organization Admin Onboarding"),
        ]

        for path, expected_text in cases:
            with self.subTest(path=path):
                response = await self.fetch("GET", path)

                self.assertEqual(response.status, 200)
                self.assertIn(expected_text, response.body)

    async def test_admin_onboard_page_replaces_turnstile_placeholders(self):
        response = await self.fetch("GET", "/admin/onboard")

        self.assertEqual(response.status, 200)
        self.assertNotIn("{{TURNSTILE", response.body)
        self.assertIn("const TURNSTILE_ENABLED = false;", response.body)

    async def test_unknown_get_path_returns_404(self):
        response = await self.fetch("GET", "/does-not-exist")

        self.assertEqual(response.status, 404)
