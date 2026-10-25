import json
import sys
import types
import unittest
from pathlib import Path
from urllib.parse import urlparse


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))


class FakeResponse:
    """Mimics the subset of the JS Response API that index.py relies on."""

    def __init__(self, body="", status=200, headers=None):
        self.body = body
        self.status = status
        self.headers = headers or {}

    @staticmethod
    def new(body="", options=None):
        options = options or {}
        status = options.get("status", 200) if isinstance(options, dict) else 200
        headers = options.get("headers", {}) if isinstance(options, dict) else {}
        return FakeResponse(body, status=status, headers=headers)


class FakeURL:
    @staticmethod
    def new(raw_url):
        parsed = urlparse(raw_url)
        return types.SimpleNamespace(pathname=parsed.path or "/")


class FakeObject:
    """Mimics JS Object.fromEntries for a list of [key, value] pairs."""

    @staticmethod
    def fromEntries(entries):
        return dict(entries)


async def fake_fetch(*_args, **_kwargs):
    # Not exercised by the tests below, but required for the module to import.
    return FakeResponse(status=200)


sys.modules["js"] = types.SimpleNamespace(
    Response=FakeResponse,
    URL=FakeURL,
    fetch=fake_fetch,
    Object=FakeObject,
)

from index import on_fetch  # noqa: E402


class Env:
    SOLANA_WALLET_ADDRESS = None
    SOLANA_RPC_URL = None


class Request:
    def __init__(self, method, path):
        self.method = method
        self.url = f"https://rewards.example.test{path}"


class OnFetchTests(unittest.IsolatedAsyncioTestCase):
    async def fetch(self, method, path):
        return await on_fetch(Request(method, path), Env())

    async def test_unknown_path_returns_404_not_500(self):
        response = await self.fetch("GET", "/nope")

        self.assertEqual(response.status, 404)
        self.assertEqual(json.loads(response.body)["error"], "Page Not Found")

    async def test_unknown_path_error_is_not_cached(self):
        response = await self.fetch("GET", "/nope")

        self.assertEqual(response.headers.get("Cache-Control"), "no-store")

    async def test_wrong_method_on_sol_balance_returns_405(self):
        response = await self.fetch("POST", "/api/sol-balance")

        self.assertEqual(response.status, 405)
        self.assertEqual(json.loads(response.body)["error"], "Method Not Allowed")

    async def test_sol_balance_without_wallet_configured_returns_500(self):
        response = await self.fetch("GET", "/api/sol-balance")

        self.assertEqual(response.status, 500)
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")

    async def test_sol_balance_success_returns_200_with_cache_header(self):
        async def fake_balance_fetch(*_args, **_kwargs):
            return types.SimpleNamespace(
                ok=True,
                status=200,
                json=self._make_json_coro({
                    "result": {"value": 2_500_000_000},
                }),
            )

        import index
        original_fetch = index.fetch
        index.fetch = fake_balance_fetch
        try:
            env = Env()
            env.SOLANA_WALLET_ADDRESS = "SomeWalletAddress"
            response = await on_fetch(Request("GET", "/api/sol-balance"), env)
        finally:
            index.fetch = original_fetch

        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers.get("Cache-Control"), "public, max-age=30")
        body = json.loads(response.body)
        self.assertEqual(body["balance"], 2.5)
        self.assertEqual(body["address"], "SomeWalletAddress")

    async def test_token_supply_success_returns_200_with_cache_header(self):
        async def fake_supply_fetch(*_args, **_kwargs):
            return types.SimpleNamespace(
                ok=True,
                status=200,
                json=self._make_json_coro({
                    "result": {"value": {"uiAmountString": "1000000"}},
                }),
            )

        import index
        original_fetch = index.fetch
        index.fetch = fake_supply_fetch
        try:
            response = await on_fetch(Request("GET", "/api/token-supply"), Env())
        finally:
            index.fetch = original_fetch

        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers.get("Cache-Control"), "public, max-age=30")
        body = json.loads(response.body)
        self.assertEqual(body["supply"], "1000000")
        self.assertEqual(body["mint"], index.BACON_MINT_ADDRESS)

    @staticmethod
    def _make_json_coro(data):
        """Returns a zero-arg async callable that resolves to a SimpleNamespace
        mimicking the RPC response's parsed JSON (so `.result.value` works)."""
        def to_namespace(obj):
            if isinstance(obj, dict):
                return types.SimpleNamespace(**{k: to_namespace(v) for k, v in obj.items()})
            return obj

        async def _coro():
            return to_namespace(data)

        return _coro

    async def test_options_preflight_returns_200_with_cors_headers(self):
        response = await self.fetch("OPTIONS", "/api/sol-balance")

        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "*")

    async def test_wrong_method_on_token_supply_returns_405(self):
        response = await self.fetch("POST", "/api/token-supply")

        self.assertEqual(response.status, 405)
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")

    async def test_404_includes_cors_headers(self):
        response = await self.fetch("GET", "/nope")

        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "*")

    async def test_sol_balance_rpc_http_error_returns_502(self):
        async def fake_fetch_http_error(*_args, **_kwargs):
            return types.SimpleNamespace(ok=False, status=503)

        import index
        original_fetch = index.fetch
        index.fetch = fake_fetch_http_error
        try:
            env = Env()
            env.SOLANA_WALLET_ADDRESS = "SomeWallet"
            response = await on_fetch(Request("GET", "/api/sol-balance"), env)
        finally:
            index.fetch = original_fetch

        self.assertEqual(response.status, 502)
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")
        self.assertIn("503", json.loads(response.body)["error"])

    async def test_sol_balance_rpc_level_error_returns_502(self):
        async def fake_fetch_rpc_error(*_args, **_kwargs):
            return types.SimpleNamespace(
                ok=True,
                status=200,
                json=self._make_json_coro({"error": "Invalid param"}),
            )

        import index
        original_fetch = index.fetch
        index.fetch = fake_fetch_rpc_error
        try:
            env = Env()
            env.SOLANA_WALLET_ADDRESS = "SomeWallet"
            response = await on_fetch(Request("GET", "/api/sol-balance"), env)
        finally:
            index.fetch = original_fetch

        self.assertEqual(response.status, 502)
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")

    async def test_sol_balance_fetch_exception_returns_500(self):
        async def fake_fetch_raises(*_args, **_kwargs):
            raise RuntimeError("network down")

        import index
        original_fetch = index.fetch
        index.fetch = fake_fetch_raises
        try:
            env = Env()
            env.SOLANA_WALLET_ADDRESS = "SomeWallet"
            response = await on_fetch(Request("GET", "/api/sol-balance"), env)
        finally:
            index.fetch = original_fetch

        self.assertEqual(response.status, 500)
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")
        self.assertEqual(json.loads(response.body)["error"], "Internal error")

    async def test_token_supply_rpc_http_error_returns_502(self):
        async def fake_fetch_http_error(*_args, **_kwargs):
            return types.SimpleNamespace(ok=False, status=500)

        import index
        original_fetch = index.fetch
        index.fetch = fake_fetch_http_error
        try:
            response = await on_fetch(Request("GET", "/api/token-supply"), Env())
        finally:
            index.fetch = original_fetch

        self.assertEqual(response.status, 502)
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")

    async def test_token_supply_fetch_exception_returns_500(self):
        async def fake_fetch_raises(*_args, **_kwargs):
            raise RuntimeError("network down")

        import index
        original_fetch = index.fetch
        index.fetch = fake_fetch_raises
        try:
            response = await on_fetch(Request("GET", "/api/token-supply"), Env())
        finally:
            index.fetch = original_fetch

        self.assertEqual(response.status, 500)
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")