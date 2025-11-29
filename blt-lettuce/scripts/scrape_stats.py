#!/usr/bin/env python3
"""
Scrape Slack Bot Activity stats from the OWASP BLT status page.

This script fetches stats from https://owaspblt.org/status_page/ and saves them
to data/stats.json for use by the GitHub Pages dashboard.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

STATUS_PAGE_URL = "https://owaspblt.org/status_page/"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "stats.json"
REQUEST_TIMEOUT = 30


def fetch_status_page():
    """Fetch the HTML content of the BLT status page."""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; BLT-Lettuce-Bot/1.0; +https://github.com/OWASP-BLT/BLT-Lettuce)"  # noqa: E501
    }

    response = requests.get(STATUS_PAGE_URL, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text


def extract_number(text):
    """Extract a numeric value from text."""
    if not text:
        return 0
    # Match a proper decimal number (digits with optional single decimal point)
    match = re.search(r"\d+(?:\.\d+)?", text.replace(",", ""))
    if match:
        value = match.group()
        return float(value) if "." in value else int(value)
    return 0


def parse_stats(html_content):
    """Parse the HTML content and extract stats."""
    soup = BeautifulSoup(html_content, "html.parser")

    stats = {
        "total_activities": 0,
        "last_24h_activities": 0,
        "active_workspaces": 0,
        "team_joins": 0,
        "commands": 0,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    # Try to find stats in the page content
    # The page structure may vary, so we try multiple approaches

    # Look for text containing statistics
    text_content = soup.get_text()

    # Extract Total Activities
    total_match = re.search(r"Total\s*Activities[:\s]*(\d[\d,]*)", text_content, re.IGNORECASE)
    if total_match:
        stats["total_activities"] = extract_number(total_match.group(1))

    # Extract Last 24h Activities
    last_24h_match = re.search(
        r"Last\s*24h?\s*Activities[:\s]*(\d[\d,]*)", text_content, re.IGNORECASE
    )
    if last_24h_match:
        stats["last_24h_activities"] = extract_number(last_24h_match.group(1))

    # Extract Active Workspaces
    workspace_match = re.search(
        r"Active\s*Workspaces[:\s]*(\d[\d,]*)", text_content, re.IGNORECASE
    )
    if workspace_match:
        stats["active_workspaces"] = extract_number(workspace_match.group(1))

    # Extract Team join count
    team_join_match = re.search(r"Team[_\s]?Join[:\s]*(\d[\d,]*)", text_content, re.IGNORECASE)
    if team_join_match:
        stats["team_joins"] = extract_number(team_join_match.group(1))

    # Extract Command count
    command_match = re.search(r"Command[:\s]*(\d[\d,]*)", text_content, re.IGNORECASE)
    if command_match:
        stats["commands"] = extract_number(command_match.group(1))

    return stats


def save_stats(stats):
    """Save stats to JSON file."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"Stats saved to {OUTPUT_FILE}")


def main():
    """Main entry point."""
    try:
        print(f"Fetching stats from {STATUS_PAGE_URL}...")
        html_content = fetch_status_page()

        print("Parsing stats...")
        stats = parse_stats(html_content)

        print(f"Extracted stats: {json.dumps(stats, indent=2)}")

        save_stats(stats)

        print("Done!")
        return 0

    except requests.RequestException as e:
        print(f"Error fetching status page: {e}", file=sys.stderr)
        return 1
    except (ValueError, KeyError, AttributeError) as e:
        print(f"Error parsing stats: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
