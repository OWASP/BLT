import json
import os
import re
import time

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://slack.com/apps"
BASE_DOMAIN = "https://slack.com"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "slack_apps.json")
REQUEST_DELAY = float(os.environ.get("SLACK_SCRAPER_DELAY", "2"))
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; BLT-Panini-SlackScraper/1.0; "
        "+https://github.com/OWASP-BLT/BLT-Panini)"
    )
}

# Known Slack App Directory category slugs used as a fallback when dynamic
# discovery fails.  These cover the full taxonomy visible at slack.com/apps.
KNOWN_CATEGORIES = [
    "communication",
    "developer-tools",
    "design",
    "file-management",
    "hr-team-culture",
    "marketing",
    "office-management",
    "project-management",
    "sales",
    "security-compliance",
    "social-fun",
    "productivity",
    "customer-support",
    "analytics",
    "finance",
]


def get_page_url(page_num, category=""):
    """Return the URL for a given page and optional category slug.

    Slack's App Directory uses the base URL for the first page and adds
    ``?page=N`` for subsequent pages.  A ``?category=<slug>`` query parameter
    restricts results to that category.
    """
    params = []
    if category:
        params.append(f"category={category}")
    if page_num > 1:
        params.append(f"page={page_num}")
    if params:
        return f"{BASE_URL}?{'&'.join(params)}"
    return BASE_URL


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
        "a[href*='/apps/A'], a[href*='/marketplace/apps/']"
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


def get_categories_from_page(html):
    """Extract category slugs from a page's HTML or __NEXT_DATA__ blob."""
    categories = set()

    # Try to find category links in the HTML (e.g. href="?category=communication")
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all("a", href=True):
        match = re.search(r"[?&]category=([^&\"']+)", tag["href"])
        if match:
            categories.add(match.group(1))

    # Also look inside __NEXT_DATA__ for category info
    script_el = soup.find("script", {"id": "__NEXT_DATA__", "type": "application/json"})
    if script_el and script_el.string:
        try:
            data = json.loads(script_el.string)
            raw = json.dumps(data)
            for match in re.finditer(r'"(?:category_slug|categorySlug)"\s*:\s*"([^"]+)"', raw):
                categories.add(match.group(1))
        except json.JSONDecodeError:
            pass

    return list(categories)


def scrape_category(category=""):
    """Scrape all pages for a given category slug (empty = no category filter)."""
    label = f"category={category!r}" if category else "all apps"
    page_num = 1
    category_apps = []
    seen_names = set()

    while True:
        url = get_page_url(page_num, category)
        print(f"Fetching {url}")
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
        except requests.RequestException as exc:
            print(f"  Request failed ({label}): {exc}")
            break

        if response.status_code != 200:
            print(f"  Stopped at page {page_num} ({label}): HTTP {response.status_code}")
            break

        apps = parse_app_cards(response.text)
        if not apps:
            print(f"  No apps found on page {page_num} ({label}). Stopping.")
            break

        new_count = 0
        for app in apps:
            key = app["app_name"].lower()
            if key not in seen_names:
                seen_names.add(key)
                category_apps.append(app)
                new_count += 1

        print(f"  Found {len(apps)} apps ({new_count} new, total for {label}: {len(category_apps)})")

        if new_count == 0:
            # All apps on this page were already seen — pagination has looped
            break

        page_num += 1
        time.sleep(REQUEST_DELAY)  # Respectful rate limiting

    return category_apps


def scrape_slack_directory():
    """Scrape all apps from the Slack App Directory by iterating categories."""
    all_apps_by_name: dict = {}

    # Fetch the main page to discover categories dynamically
    print(f"Fetching main page: {BASE_URL}")
    discovered_categories: list = []
    try:
        resp = requests.get(BASE_URL, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            discovered_categories = get_categories_from_page(resp.text)
            print(f"Discovered {len(discovered_categories)} categories from main page")
        else:
            print(f"Main page returned HTTP {resp.status_code}")
    except requests.RequestException as exc:
        print(f"Could not fetch main page: {exc}")

    # Merge discovered categories with the known fallback list, preserving order
    categories_to_scrape = list(
        dict.fromkeys(discovered_categories + KNOWN_CATEGORIES)
    )

    # Always include a pass with no category filter to catch apps not in any category
    for category in [""] + categories_to_scrape:
        apps = scrape_category(category)
        for app in apps:
            key = app["app_name"].lower()
            if key not in all_apps_by_name:
                all_apps_by_name[key] = app

        print(f"Running total after {repr(category) if category else 'no-category'}: {len(all_apps_by_name)} unique apps")

    return list(all_apps_by_name.values())


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
