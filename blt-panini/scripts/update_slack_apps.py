import json
import os
import time

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://slack.com/apps"
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


def parse_app_cards(html):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("a.app_card, a.integration-card, div.app_card_wrapper a")
    results = []
    for card in cards:
        href = card.get("href", "")
        name_el = (
            card.select_one(".app_card__title")
            or card.select_one(".integration-card__title")
            or card.select_one("h2")
            or card.select_one("h3")
        )
        desc_el = (
            card.select_one(".app_card__description")
            or card.select_one(".integration-card__description")
            or card.select_one("p")
        )
        cat_el = (
            card.select_one(".app_card__category")
            or card.select_one(".integration-card__category")
            or card.select_one(".category")
        )

        name = name_el.get_text(strip=True) if name_el else ""
        description = desc_el.get_text(strip=True) if desc_el else ""
        category = cat_el.get_text(strip=True) if cat_el else ""

        if href and not href.startswith("http"):
            href = f"https://slack.com{href}"

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
