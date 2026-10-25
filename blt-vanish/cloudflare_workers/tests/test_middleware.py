import middleware


class Request:
    def __init__(self, headers=None, method="GET"):
        self.headers = headers or {}
        self.method = method


def test_rate_limit_allows_first_100_requests():
    request = Request({"cf-connecting-ip": "192.0.2.1"})

    for _ in range(middleware.MAX_REQUESTS_PER_WINDOW):
        assert middleware.rate_limit_middleware(request) is None


def test_rate_limit_rejects_request_101():
    request = Request({"cf-connecting-ip": "192.0.2.2"})

    for _ in range(middleware.MAX_REQUESTS_PER_WINDOW):
        assert middleware.rate_limit_middleware(request) is None

    response = middleware.rate_limit_middleware(request)

    assert response.status == 429
    assert "Too Many Requests" in response.text
    assert response.headers["Access-Control-Allow-Origin"] == "*"


def test_rate_limit_uses_forwarded_ip_when_cf_ip_missing():
    request = Request({"x-forwarded-for": "192.0.2.3"})

    assert middleware.rate_limit_middleware(request) is None
    assert "192.0.2.3" in middleware._ip_requests


def test_alert_post_requires_json_content_type():
    request = Request({"content-type": "text/plain"}, method="POST")

    response = middleware.alert_routing_middleware(request, "/api/alerts")

    assert response.status == 400
    assert "Invalid Content-Type" in response.text


def test_alert_put_accepts_json_content_type():
    request = Request({"content-type": "application/json"}, method="PUT")

    assert middleware.alert_routing_middleware(request, "/api/alerts") is None


def test_non_alert_post_does_not_require_json_content_type():
    request = Request({"content-type": "text/plain"}, method="POST")

    assert middleware.alert_routing_middleware(request, "/api/brokers") is None
