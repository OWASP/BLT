"""
Tests for Worker-level shared API-key enforcement.
"""

import json
import importlib
import sys
import types
from unittest.mock import AsyncMock, patch

import pytest


workers_mod = types.ModuleType("workers")


class WorkerEntrypoint:
    pass


class WorkerResponse:
    @staticmethod
    def json(data, status=200, headers=None):
        return {"status": status, "headers": headers or {}, "data": data}


workers_mod.WorkerEntrypoint = WorkerEntrypoint
workers_mod.Response = WorkerResponse
sys.modules["workers"] = workers_mod

if "main" in sys.modules:
    main = importlib.reload(sys.modules["main"])
else:
    main = importlib.import_module("main")


class MockHeaders(dict):
    def get(self, key, default=None):
        for existing_key, value in self.items():
            if existing_key.lower() == key.lower():
                return value
        return default


class MockRequest:
    def __init__(self, method="GET", url="https://api.example.com/bugs", headers=None):
        self.method = method
        self.url = url
        self.headers = MockHeaders(headers or {})


class MockEnv:
    BLT_API_KEY = "docs-static-key"


def _response_data(response):
    if hasattr(response, "body"):
        return json.loads(response.body)
    return response.get("data", {})


@pytest.mark.asyncio
async def test_on_fetch_rejects_protected_request_without_api_key_before_db():
    worker = main.Default()
    worker.env = MockEnv()
    request = MockRequest(url="https://api.example.com/bugs")

    with patch("main.get_db_safe", AsyncMock()) as get_db, \
         patch.object(main.router, "handle", AsyncMock()) as handle:
        response = await worker.on_fetch(request)

    assert response.status == 401
    assert _response_data(response)["message"] == "Missing API key"
    get_db.assert_not_called()
    handle.assert_not_called()


@pytest.mark.asyncio
async def test_on_fetch_rejects_protected_request_with_invalid_api_key_before_db():
    worker = main.Default()
    worker.env = MockEnv()
    request = MockRequest(headers={"X-BLT-API-Key": "wrong-key"})

    with patch("main.get_db_safe", AsyncMock()) as get_db, \
         patch.object(main.router, "handle", AsyncMock()) as handle:
        response = await worker.on_fetch(request)

    assert response.status == 401
    assert _response_data(response)["message"] == "Invalid API key"
    get_db.assert_not_called()
    handle.assert_not_called()


@pytest.mark.asyncio
async def test_on_fetch_allows_protected_request_with_valid_api_key():
    worker = main.Default()
    worker.env = MockEnv()
    request = MockRequest(headers={"X-BLT-API-Key": "docs-static-key"})
    expected_response = object()

    with patch("main.get_db_safe", AsyncMock()) as get_db, \
         patch.object(main.router, "handle", AsyncMock(return_value=expected_response)) as handle:
        response = await worker.on_fetch(request)

    assert response is expected_response
    get_db.assert_awaited_once_with(worker.env)
    handle.assert_awaited_once_with(request, worker.env)


@pytest.mark.asyncio
async def test_on_fetch_allows_health_without_api_key():
    worker = main.Default()
    worker.env = MockEnv()
    request = MockRequest(url="https://api.example.com/health")
    expected_response = object()

    with patch("main.get_db_safe", AsyncMock()) as get_db, \
         patch.object(main.router, "handle", AsyncMock(return_value=expected_response)) as handle:
        response = await worker.on_fetch(request)

    assert response is expected_response
    get_db.assert_awaited_once_with(worker.env)
    handle.assert_awaited_once_with(request, worker.env)


@pytest.mark.asyncio
async def test_on_fetch_allows_options_preflight_without_api_key():
    worker = main.Default()
    worker.env = MockEnv()
    request = MockRequest(method="OPTIONS", url="https://api.example.com/bugs")

    with patch("main.get_db_safe", AsyncMock()) as get_db, \
         patch.object(main.router, "handle", AsyncMock()) as handle:
        response = await worker.on_fetch(request)

    assert response.status == 204
    get_db.assert_not_called()
    handle.assert_not_called()
