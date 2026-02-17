#!/usr/bin/env python3
"""Quick script to test the Issues API endpoints locally."""

import requests
import json

BASE_URL = "http://localhost:8787"

def test_issues_list():
    """Test GET /issues endpoint."""
    print("Testing GET /issues...")
    try:
        response = requests.get(f"{BASE_URL}/issues")
        print(f"Status: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")
        print(f"Response text: {response.text if 'response' in locals() else 'N/A'}")

def test_issues_list_with_pagination():
    """Test GET /issues with pagination."""
    print("\nTesting GET /issues?page=1&per_page=2...")
    try:
        response = requests.get(f"{BASE_URL}/issues?page=1&per_page=2")
        print(f"Status: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")
        print(f"Response text: {response.text if 'response' in locals() else 'N/A'}")

def test_issues_filter_by_status():
    """Test GET /issues with status filter."""
    print("\nTesting GET /issues?status=open...")
    try:
        response = requests.get(f"{BASE_URL}/issues?status=open")
        print(f"Status: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")
        print(f"Response text: {response.text if 'response' in locals() else 'N/A'}")

def test_issue_detail():
    """Test GET /issues/{id} endpoint."""
    print("\nTesting GET /issues/1...")
    try:
        response = requests.get(f"{BASE_URL}/issues/1")
        print(f"Status: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")
        print(f"Response text: {response.text if 'response' in locals() else 'N/A'}")

def test_issue_with_screenshots_and_tags():
    """Test GET /issues/{id} with screenshots and tags."""
    print("\nTesting GET /issues/1 (with screenshots and tags)...")
    try:
        response = requests.get(f"{BASE_URL}/issues/1")
        data = response.json()
        print(f"Status: {response.status_code}")
        
        if data.get("success") and data.get("data"):
            issue = data["data"]
            print(f"\nIssue Details:")
            print(f"  ID: {issue.get('id')}")
            print(f"  Description: {issue.get('description')[:50]}...")
            print(f"  Status: {issue.get('status')}")
            print(f"  Score: {issue.get('score')}")
            print(f"  Verified: {issue.get('verified')}")
            print(f"  Domain: {issue.get('domain_name')}")
            print(f"  Screenshots: {len(issue.get('screenshots', []))}")
            print(f"  Tags: {[tag.get('name') for tag in issue.get('tags', [])]}")
        else:
            print(f"Response:")
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error: {e}")
        print(f"Response text: {response.text if 'response' in locals() else 'N/A'}")

def test_issue_not_found():
    """Test GET /issues/{id} with invalid ID."""
    print("\nTesting GET /issues/999 (not found)...")
    try:
        response = requests.get(f"{BASE_URL}/issues/999")
        print(f"Status: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")
        print(f"Response text: {response.text if 'response' in locals() else 'N/A'}")

def test_issue_invalid_id():
    """Test GET /issues/{id} with invalid ID format."""
    print("\nTesting GET /issues/invalid (invalid ID)...")
    try:
        response = requests.get(f"{BASE_URL}/issues/invalid")
        print(f"Status: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")
        print(f"Response text: {response.text if 'response' in locals() else 'N/A'}")

def test_create_issue():
    """Test POST /issues endpoint."""
    print("\nTesting POST /issues...")
    try:
        payload = {
            "url": "https://test.example.com/vulns",
            "description": "Test vulnerability created via API",
            "markdown_description": "## Test Vulnerability\n\nThis is a test issue.",
            "status": "open"
        }
        
        response = requests.post(
            f"{BASE_URL}/issues",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")
        print(f"Response text: {response.text if 'response' in locals() else 'N/A'}")

def test_create_issue_missing_fields():
    """Test POST /issues with missing required fields."""
    print("\nTesting POST /issues (missing fields)...")
    try:
        payload = {
            "url": "https://test.example.com/vulns"
            # Missing description
        }
        
        response = requests.post(
            f"{BASE_URL}/issues",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")
        print(f"Response text: {response.text if 'response' in locals() else 'N/A'}")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Issues API Endpoints")
    print("=" * 60)
    
    test_issues_list()
    test_issues_list_with_pagination()
    test_issues_filter_by_status()
    test_issue_detail()
    test_issue_with_screenshots_and_tags()
    test_issue_not_found()
    test_issue_invalid_id()
    test_create_issue()
    test_create_issue_missing_fields()
    
    print("\n" + "=" * 60)
    print("Testing Complete!")
    print("=" * 60)
