
import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests

from scripts.update_slack_apps import (
    BASE_URL,
    get_page_url,
    main,
    merge_apps,
    parse_app_cards,
    scrape_category,
)


class TestMergeApps(unittest.TestCase):
    def test_existing_app_keeps_curated_security_fields(self):
        existing = [
            {
                "app_name": "SecureApp",
                "category": "",
                "developer": "Trusted Developer",
                "security_rating": "A",
                "permissions": ["channels:read"],
                "data_access": "Limited",
                "verified": True,
                "security_notes": "Manually reviewed",
                "source_url": "https://slack.com/apps/old",
                "privacy_policy_url": "https://example.com/privacy",
            }
        ]
        scraped = [
            {
                "app_name": "SecureApp",
                "category": "Security",
                "description": "Scraped description",
                "source_url": "https://slack.com/apps/secure",
            }
        ]

        merged, added = merge_apps(existing, scraped)

        self.assertEqual(added, 0)
        self.assertEqual(len(merged), 1)
        app = merged[0]
        self.assertEqual(app["security_rating"], "A")
        self.assertEqual(app["permissions"], ["channels:read"])
        self.assertEqual(app["data_access"], "Limited")
        self.assertTrue(app["verified"])
        self.assertEqual(app["security_notes"], "Manually reviewed")
        self.assertEqual(
            app["privacy_policy_url"], "https://example.com/privacy"
        )
        self.assertEqual(app["developer"], "Trusted Developer")
        self.assertEqual(app["category"], "Security")
        self.assertEqual(app["source_url"], "https://slack.com/apps/secure")

    def test_new_app_gets_security_defaults(self):
        scraped = [
            {
                "app_name": "NewApp",
                "category": "Productivity",
                "description": "Helps teams work together.",
                "source_url": "https://slack.com/apps/new",
            }
        ]

        merged, added = merge_apps([], scraped)

        self.assertEqual(added, 1)
        self.assertEqual(
            merged[0],
            {
                "app_name": "NewApp",
                "category": "Productivity",
                "developer": "",
                "security_rating": "",
                "permissions": [],
                "data_access": "",
                "verified": False,
                "security_notes": "Helps teams work together.",
                "source_url": "https://slack.com/apps/new",
                "privacy_policy_url": "",
            },
        )

    def test_app_names_are_matched_case_insensitively(self):
        existing = [{"app_name": "SecureApp", "security_rating": "A"}]
        scraped = [
            {
                "app_name": "secureapp",
                "source_url": "https://slack.com/apps/secure",
                "category": "Security",
            }
        ]

        merged, added = merge_apps(existing, scraped)

        self.assertEqual(added, 0)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["security_rating"], "A")
        self.assertEqual(merged[0]["category"], "Security")


class TestParseAppCards(unittest.TestCase):
    def test_parses_card_html(self):
        html = """
        <html><body>
          <a class="app_card" href="/apps/A123-example">
            <h3 class="app_card__title">Example App</h3>
            <p class="app_card__description">An example integration.</p>
            <span class="app_card__category">Productivity</span>
          </a>
        </body></html>
        """

        apps = parse_app_cards(html)

        self.assertEqual(
            apps,
            [
                {
                    "app_name": "Example App",
                    "source_url": "https://slack.com/apps/A123-example",
                    "description": "An example integration.",
                    "category": "Productivity",
                }
            ],
        )

    def test_parses_embedded_next_data(self):
        payload = {
            "props": {
                "pageProps": {
                    "apps": [
                        {
                            "id": "A456",
                            "name": "Calendar App",
                            "description": "Syncs team calendars.",
                            "category": "Productivity",
                        }
                    ]
                }
            }
        }
        html = (
            '<script id="__NEXT_DATA__" type="application/json">'
            + json.dumps(payload)
            + "</script>"
        )

        apps = parse_app_cards(html)

        self.assertEqual(
            apps,
            [
                {
                    "app_name": "Calendar App",
                    "source_url": "https://slack.com/apps/A456",
                    "description": "Syncs team calendars.",
                    "category": "Productivity",
                }
            ],
        )

    def test_malformed_next_data_falls_back_to_html(self):
        html = """
        <html><body>
          <script id="__NEXT_DATA__" type="application/json">
            {invalid json}
          </script>
          <a class="app_card" href="/apps/A123-fallback">
            <h3 class="app_card__title">Fallback App</h3>
            <p class="app_card__description">Parsed from HTML.</p>
            <span class="app_card__category">Security</span>
          </a>
        </body></html>
        """

        apps = parse_app_cards(html)

        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0]["app_name"], "Fallback App")
        self.assertEqual(
            apps[0]["source_url"],
            "https://slack.com/apps/A123-fallback",
        )
        self.assertEqual(apps[0]["description"], "Parsed from HTML.")
        self.assertEqual(apps[0]["category"], "Security")

    def test_finds_apps_in_nested_json(self):
        payload = {
            "props": {
                "pageProps": {
                    "results": [
                        {
                            "appName": "Nested App",
                            "id": "A789",
                            "description": "Found in nested data.",
                        }
                    ]
                }
            }
        }
        html = (
            '<script id="__NEXT_DATA__" type="application/json">'
            + json.dumps(payload)
            + "</script>"
        )

        apps = parse_app_cards(html)

        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0]["app_name"], "Nested App")
        self.assertEqual(
            apps[0]["source_url"], "https://slack.com/apps/A789"
        )


class TestPageUrl(unittest.TestCase):
    def test_first_page_uses_base_url(self):
        self.assertEqual(get_page_url(1), BASE_URL)

    def test_subsequent_page_includes_page_number(self):
        self.assertEqual(get_page_url(3), f"{BASE_URL}?page=3")

    def test_category_and_page_parameters_are_combined(self):
        self.assertEqual(
            get_page_url(2, "security-compliance"),
            f"{BASE_URL}?category=security-compliance&page=2",
        )


class TestScrapeCategory(unittest.TestCase):
    def test_stops_when_page_repeats_apps(self):
        html = """
        <a class="app_card" href="/apps/A123">
          <h3 class="app_card__title">Repeated App</h3>
        </a>
        """
        response = Mock(status_code=200, text=html)

        with (
            patch(
                "scripts.update_slack_apps.requests.get",
                return_value=response,
            ) as mock_get,
            patch("scripts.update_slack_apps.time.sleep"),
        ):
            apps = scrape_category()

        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0]["app_name"], "Repeated App")
        self.assertEqual(mock_get.call_count, 2)

    def test_http_errors_stop_scraping_without_crashing(self):
        for status_code in (429, 500):
            with self.subTest(status_code=status_code):
                response = Mock(status_code=status_code, text="Error")

                with patch(
                    "scripts.update_slack_apps.requests.get",
                    return_value=response,
                ):
                    apps = scrape_category("security-compliance")

                self.assertEqual(apps, [])

    def test_request_exception_stops_scraping_without_crashing(self):
        with patch(
            "scripts.update_slack_apps.requests.get",
            side_effect=requests.RequestException("Connection failed"),
        ):
            apps = scrape_category()

        self.assertEqual(apps, [])


class TestMain(unittest.TestCase):
    def test_empty_scrape_preserves_existing_json(self):
        existing_apps = [
            {
                "app_name": "KeepMe",
                "security_rating": "A",
                "verified": True,
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "slack_apps.json")

            with open(output_path, "w", encoding="utf-8") as file:
                json.dump(existing_apps, file)

            with (
                patch(
                    "scripts.update_slack_apps.OUTPUT_FILE",
                    output_path,
                ),
                patch(
                    "scripts.update_slack_apps.scrape_slack_directory",
                    return_value=[],
                ),
            ):
                main()

            with open(output_path, encoding="utf-8") as file:
                saved_apps = json.load(file)

        self.assertEqual(saved_apps, existing_apps)


if __name__ == "__main__":
    unittest.main()
