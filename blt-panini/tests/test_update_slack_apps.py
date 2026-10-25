
import json
import unittest

from scripts.update_slack_apps import (
    _find_apps_in_json,
    _parse_next_data,
    merge_apps,
    parse_app_cards,
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
        merged, added = merge_apps(
            [],
            [
                {
                    "app_name": "NewApp",
                    "category": "Productivity",
                    "description": "Helps teams work together.",
                    "source_url": "https://slack.com/apps/new",
                }
            ],
        )

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

    def test_parses_next_data_json_blob(self):
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

    def test_invalid_next_data_returns_empty_list(self):
        html = (
            '<script id="__NEXT_DATA__" type="application/json">'
            '{invalid json}'
            "</script>"
        )

        self.assertEqual(_parse_next_data(html), [])

    def test_finds_apps_in_nested_json(self):
        data = {
            "props": {
                "pageProps": {
                    "results": [
                        {"appName": "Nested App", "id": "A789"}
                    ]
                }
            }
        }

        self.assertEqual(
            _find_apps_in_json(data),
            [{"appName": "Nested App", "id": "A789"}],
        )


if __name__ == "__main__":
    unittest.main()
