"""fetch() init dicts are converted to JS objects on the Workers runtime.

A bare Python dict reaches JS fetch as a PyProxy whose ``method``/``body``
properties read as undefined, so a POST silently becomes a body-less GET
(GitHub's token exchange then fails). These tests stand in for the ``js`` and
``pyodide.ffi`` modules and check every outbound call site converts.
"""

from pathlib import Path
import sys
import types

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from js_fetch import fetch_init  # noqa: E402


class Converted(dict):
    """What to_js(..., dict_converter=Object.fromEntries) would produce."""


class FakeResp:
    status = 200

    async def text(self):
        return '{"access_token": "t", "login": "octo", "id": 1}'


@pytest.fixture
def fake_runtime(monkeypatch):
    calls = []

    async def fetch(url, init):
        calls.append((url, init))
        return FakeResp()

    js = types.ModuleType("js")
    js.fetch = fetch
    js.Object = types.SimpleNamespace(fromEntries=object())
    pyodide = types.ModuleType("pyodide")
    ffi = types.ModuleType("pyodide.ffi")

    def to_js(value, dict_converter=None):
        assert dict_converter is js.Object.fromEntries
        return Converted(value)

    ffi.to_js = to_js
    pyodide.ffi = ffi
    monkeypatch.setitem(sys.modules, "js", js)
    monkeypatch.setitem(sys.modules, "pyodide", pyodide)
    monkeypatch.setitem(sys.modules, "pyodide.ffi", ffi)
    return calls


def test_fetch_init_passthrough_without_runtime():
    assert fetch_init({"method": "POST"}) == {"method": "POST"}


def test_fetch_init_converts_on_runtime(fake_runtime):
    out = fetch_init({"method": "POST", "headers": {"A": "b"}})
    assert isinstance(out, Converted) and out["method"] == "POST"


@pytest.mark.asyncio
async def test_oauth_token_exchange_sends_a_real_post(fake_runtime):
    import oauth_github

    status, body = await oauth_github._http_json(
        oauth_github.GITHUB_TOKEN_URL, method="POST", headers={"Accept": "application/json"}, body=b"code=x",
    )
    assert status == 200 and body["access_token"] == "t"
    url, init = fake_runtime[0]
    assert isinstance(init, Converted)
    assert init["method"] == "POST" and init["body"] == "code=x"


@pytest.mark.asyncio
async def test_other_call_sites_convert(fake_runtime):
    import blt_api_client
    import detect_service
    import disclosure
    import events_service

    await blt_api_client._js_fetch_post_json("https://api.example/v2/bugs", {}, {"a": 1})
    await events_service._js_fetch("https://hook.example/", "POST", {}, b"{}")
    await disclosure.fetch_text("https://site.example/.well-known/security.txt")
    await detect_service._default_fetch("https://site.example/")
    assert len(fake_runtime) == 4
    assert all(isinstance(init, Converted) for _url, init in fake_runtime)
