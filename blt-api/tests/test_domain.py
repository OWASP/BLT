#!/usr/bin/env python3
"""Quick script to test the API locally."""

import requests
import json

BASE_URL = "http://localhost:8787"

def test_domains_list():
    """Test GET /domains endpoint."""
    print("Testing GET /domains...")
    try:
        response = requests.get(f"{BASE_URL}/domains")
        print(f"Status: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")
        print(f"Response text: {response.text if 'response' in locals() else 'N/A'}")

def test_domain_detail():
    """Test GET /domains/{id} endpoint."""
    print("\nTesting GET /domains/1...")
    try:
        response = requests.get(f"{BASE_URL}/domains/1")
        print(f"Status: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")
        print(f"Response text: {response.text if 'response' in locals() else 'N/A'}")

def test_domain_tags():
    """Test GET /domains/{id}/tags endpoint."""
    print("\nTesting GET /domains/1/tags...")
    try:
        response = requests.get(f"{BASE_URL}/domains/1/tags")
        print(f"Status: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")
        print(f"Response text: {response.text if 'response' in locals() else 'N/A'}")

if __name__ == "__main__":
    test_domains_list()
    test_domain_detail()
    test_domain_tags()
