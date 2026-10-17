"""Workers FFI header probe must forward Cookie for OAuth sessions."""

from types import SimpleNamespace

from worker import BLTWorker


class JsHeaders:
    """Cloudflare-like Headers: .get() works, .items() is unreliable."""

    def __init__(self, data):
        self._data = {str(k).lower(): str(v) for k, v in data.items()}

    def get(self, name):
        return self._data.get(str(name).lower())


class Req:
    def __init__(self, headers):
        self.headers = headers


def test_get_request_headers_forwards_cookie_from_js_headers():
    worker = BLTWorker(SimpleNamespace(DB=None))
    headers = worker.get_request_headers(
        Req(JsHeaders({
            "Authorization": "Bearer triage-token",
            "Cookie": "ng_session=abc",
            "X-BLT-Body-Digest": "sha256=00",
        }))
    )
    assert headers.get("Cookie") == "ng_session=abc" or headers.get("cookie") == "ng_session=abc"
    assert "Authorization" in headers or "authorization" in headers
