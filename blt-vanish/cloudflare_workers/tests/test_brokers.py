import json

from brokers import BROKERS, handle_brokers_request


def response_json(response):
    return json.loads(response.text)


def test_broker_list_returns_all_brokers():
    response = handle_brokers_request("/api/brokers")

    assert response.status == 200
    assert response_json(response) == BROKERS


def test_broker_detail_returns_matching_broker():
    response = handle_brokers_request("/api/brokers/whitepages")

    assert response.status == 200
    assert response_json(response)["id"] == "whitepages"
    assert response_json(response)["name"] == "Whitepages"


def test_unknown_broker_returns_404():
    response = handle_brokers_request("/api/brokers/not-a-real-broker")

    assert response.status == 404
    assert response_json(response) == {"error": "Broker not found"}
