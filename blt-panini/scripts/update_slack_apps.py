import json
import os
import time

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://slack.com/marketplace/apps"
BASE_DOMAIN = "https://slack.com"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "slack_apps.json")
REQUEST_DELAY = float(os.environ.get("SLACK_SCRAPER_DELAY", "2"))
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; BLT-Panini-SlackScraper/1.0; "
        "+https://github.com/OWASP-BLT/BLT-Panini)"
    )
}


def get_page_url(page_num):
    return f"{BASE_URL}?page={page_num}"


def _find_apps_in_json(data, depth=0):
    """Recursively search a JSON structure for a list of app-like objects."""
    if depth > 10:
        return []
    if isinstance(data, list) and len(data) > 0:
        first = data[0]
        if isinstance(first, dict) and any(
            k in first for k in ("name", "app_name", "appName", "title", "listing")
        ):
            return data
        for item in data:
            result = _find_apps_in_json(item, depth + 1)
            if result:
                return result
    if isinstance(data, dict):
        for key in ("apps", "listings", "items", "results", "integrations"):
            if key in data and isinstance(data[key], list) and data[key]:
                result = _find_apps_in_json(data[key], depth + 1)
                if result:
                    return result
        for value in data.values():
            if isinstance(value, (dict, list)):
                result = _find_apps_in_json(value, depth + 1)
                if result:
                    return result
    return []


def _parse_next_data(html):
    """Extract app listings from a Next.js __NEXT_DATA__ JSON blob."""
    soup = BeautifulSoup(html, "html.parser")
    script_el = soup.find("script", {"id": "__NEXT_DATA__", "type": "application/json"})
    if not script_el or not script_el.string:
        return []
    try:
        data = json.loads(script_el.string)
    except json.JSONDecodeError:
        return []

    raw_apps = _find_apps_in_json(data)
    results = []
    for app in raw_apps:
        if not isinstance(app, dict):
            continue
        name = (
            app.get("name")
            or app.get("app_name")
            or app.get("appName")
            or app.get("title")
            or ""
        )
        description = (
            app.get("description")
            or app.get("short_description")
            or app.get("shortDescription")
            or ""
        )
        category = (
            app.get("category")
            or app.get("categoryName")
            or app.get("category_name")
            or ""
        )
        app_id = app.get("id") or app.get("appId") or app.get("app_id") or ""
        href = app.get("url") or app.get("href") or app.get("permalink") or ""
        if not href and app_id:
            href = f"{BASE_URL}/{app_id}"
        if href and not href.startswith("http"):
            href = f"{BASE_DOMAIN}{href}"
        if name:
            results.append(
                {
                    "app_name": name,
                    "source_url": href,
                    "description": description,
                    "category": category,
                }
            )
    return results


def parse_app_cards(html):
    # Try Next.js __NEXT_DATA__ JSON blob first (Slack Marketplace uses Next.js)
    next_data_apps = _parse_next_data(html)
    if next_data_apps:
        return next_data_apps

    # Fall back to CSS selector-based HTML parsing
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(
        "a.app_card, a.integration-card, div.app_card_wrapper a, "
        "li[class*='app'] a, article[class*='app'], "
        "a[href*='/marketplace/apps/'], a[href*='/apps/A']"
    )
    results = []
    for card in cards:
        href = card.get("href", "")
        name_el = (
            card.select_one(".app_card__title")
            or card.select_one(".integration-card__title")
            or card.select_one("[class*='title']")
            or card.select_one("[class*='name']")
            or card.select_one("h2")
            or card.select_one("h3")
        )
        desc_el = (
            card.select_one(".app_card__description")
            or card.select_one(".integration-card__description")
            or card.select_one("[class*='description']")
            or card.select_one("p")
        )
        cat_el = (
            card.select_one(".app_card__category")
            or card.select_one(".integration-card__category")
            or card.select_one("[class*='category']")
        )

        name = name_el.get_text(strip=True) if name_el else ""
        description = desc_el.get_text(strip=True) if desc_el else ""
        category = cat_el.get_text(strip=True) if cat_el else ""

        if href and not href.startswith("http"):
            href = f"{BASE_DOMAIN}{href}"

        if name:
            results.append(
                {
                    "app_name": name,
                    "source_url": href,
                    "description": description,
                    "category": category,
                }
            )
    return results


def load_existing_apps(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def merge_apps(existing, scraped):
    existing_by_name = {app["app_name"].lower(): app for app in existing}
    updated = list(existing)

    added = 0
    for scraped_app in scraped:
        key = scraped_app["app_name"].lower()
        if key in existing_by_name:
            # Update basic fields that may change; preserve curated security data
            entry = existing_by_name[key]
            if scraped_app.get("source_url"):
                entry["source_url"] = scraped_app["source_url"]
            if scraped_app.get("category") and not entry.get("category"):
                entry["category"] = scraped_app["category"]
        else:
            # New app — add with empty security defaults
            new_entry = {
                "app_name": scraped_app["app_name"],
                "category": scraped_app.get("category", ""),
                "developer": "",
                "security_rating": "",
                "permissions": [],
                "data_access": "",
                "verified": False,
                "security_notes": scraped_app.get("description", ""),
                "source_url": scraped_app.get("source_url", ""),
                "privacy_policy_url": "",
            }
            updated.append(new_entry)
            existing_by_name[key] = new_entry
            added += 1

    return updated, added


def scrape_slack_directory():
    page_num = 1
    all_apps = []

    while True:
        url = get_page_url(page_num)
        print(f"Fetching {url}")
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
        except requests.RequestException as exc:
            print(f"Request failed: {exc}")
            break

        if response.status_code != 200:
            print(f"Stopped at page {page_num}: HTTP {response.status_code}")
            break

        apps = parse_app_cards(response.text)
        if not apps:
            print(f"No apps found on page {page_num}. Stopping.")
            break

        all_apps.extend(apps)
        print(f"  Found {len(apps)} apps (total so far: {len(all_apps)})")
        page_num += 1
        time.sleep(REQUEST_DELAY)  # Respectful rate limiting

    return all_apps


def main():
    output_path = os.path.abspath(OUTPUT_FILE)
    print(f"Output file: {output_path}")

    existing_apps = load_existing_apps(output_path)
    print(f"Existing apps in JSON: {len(existing_apps)}")

    scraped_apps = scrape_slack_directory()
    print(f"Total apps scraped: {len(scraped_apps)}")

    if not scraped_apps:
        print("No apps scraped. The file will not be modified.")
        return

    merged, added = merge_apps(existing_apps, scraped_apps)
    print(f"New apps added: {added}")
    print(f"Total apps after merge: {len(merged)}")

    if merged == existing_apps:
        print("No changes detected. Skipping file write.")
        return

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=4, ensure_ascii=False)

    print(f"Updated {output_path}")


if __name__ == "__main__":
    main()
