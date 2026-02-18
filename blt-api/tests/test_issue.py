#!/usr/bin/env python3
"""Test script for BLT API endpoints"""

import requests
import json
import sys

BASE_URL = "http://localhost:8787"

def test(name, method, endpoint, data=None, expected=200):
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{name}")
    print(f"{method} {endpoint}")
    
    try:
        if method == "GET":
            r = requests.get(url, timeout=5)
        elif method == "POST":
            r = requests.post(url, json=data, timeout=5)
        
        status = "PASS" if r.status_code == expected else "FAIL"
        print(f"Status: {r.status_code} [{status}]")
        
        if r.status_code != expected:
            print(f"Response: {r.text[:200]}")
        
        return r.json() if r.headers.get('content-type', '').startswith('application/json') else None
        
    except requests.exceptions.ConnectionError:
        print(f"ERROR: Cannot connect to {BASE_URL}")
        print("Start server: wrangler dev --port 8788")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        return None

if __name__ == "__main__":
    print("BLT API ENDPOINT TESTS")
    print("=" * 60)
    
    # HEALTH CHECK
    test("Health Check", "GET", "/")
    test("Health Endpoint", "GET", "/health")
    
    # DOMAINS
    test("List Domains", "GET", "/domains")
    test("List Domains (Paginated)", "GET", "/domains?page=1&per_page=2")
    test("Get Domain", "GET", "/domains/1")
    test("Get Domain Tags", "GET", "/domains/1/tags")
    test("Get Invalid Domain", "GET", "/domains/999", expected=404)
    
    # ISSUES
    test("List Issues", "GET", "/issues")
    test("List Issues (Paginated)", "GET", "/issues?page=1&per_page=2")
    test("Filter Issues by Status", "GET", "/issues?status=open")
    test("Filter Issues by Domain", "GET", "/issues?domain=1")
    test("Filter Issues by Verified", "GET", "/issues?verified=true")
    test("Get Issue with Screenshots & Tags", "GET", "/issues/1")
    test("Get Invalid Issue", "GET", "/issues/999", expected=404)
    test("Get Issue Invalid ID", "GET", "/issues/abc", expected=400)
    
    # CREATE ISSUE
    new_issue = {
        "url": "https://test.example.com/api/test",
        "description": "Test issue created via API test script",
        "status": "open",
        "domain": 1,
        "score": 60
    }
    result = test("Create Issue", "POST", "/issues", data=new_issue, expected=201)
    
    if result and result.get("data", {}).get("id"):
        issue_id = result["data"]["id"]
        test(f"Fetch Created Issue", "GET", f"/issues/{issue_id}")
    
    test("Create Issue Missing Fields", "POST", "/issues", data={"url": "test"}, expected=400)
    
    # SEARCH
    test("Search Issues", "GET", "/issues/search?q=XSS")
    test("Search Issues No Query", "GET", "/issues/search", expected=400)
    
    print("\n" + "=" * 60)
    print("TESTS COMPLETED")
    print("=" * 60)
