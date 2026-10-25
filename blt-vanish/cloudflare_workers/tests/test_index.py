import asyncio
import json

from index import Default
import middleware


class Request:
    def __init__(self, method, path, headers=None):
        self.method = method
        self.url = f"https://example.test{path}"
        self.headers = headers or {}


def fetch(method, path, headers=None):
    return asyncio.run(Default().fetch(Request(method, path, headers)))


def test_broker_list_route():
    response = fetch("GET", "/api/brokers")

    assert response.status == 200
    assert len(json.loads(response.text)) > 0


def test_broker_detail_route():
    response = fetch("GET", "/api/brokers/whitepages")

    assert response.status == 200
    assert json.loads(response.text)["id"] == "whitepages"


def test_unknown_broker_route_returns_404():
    response = fetch("GET", "/api/brokers/unknown-broker")

    assert response.status == 404


def test_options_request_bypasses_rate_limit():
    middleware._ip_requests["192.0.2.10"] = [
        100.0
    ] * middleware.MAX_REQUESTS_PER_WINDOW

    response = fetch(
        "OPTIONS",
        "/api/brokers",
        {"cf-connecting-ip": "192.0.2.10"},
    )

    assert response.status == 200
    assert response.headers["Access-Control-Allow-Methods"] == "GET, OPTIONS"


def test_unknown_path_returns_404():
    response = fetch("GET", "/not-a-real-route")

    assert response.status == 404
    assert response.text == "Not Found"


def test_alert_route_rejects_wrong_content_type():
    response = fetch(
        "POST",
        "/api/alerts",
        {"cf-connecting-ip": "192.0.2.11", "content-type": "text/plain"},
    )

    assert response.status == 400
