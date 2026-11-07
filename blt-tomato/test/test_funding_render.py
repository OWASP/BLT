"""Regression tests: the funding page escapes project names and FUNDING.yml values (controlled by
third-party repo owners) and only links http(s) URLs."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / ".github/scripts/funding/owasp_funding_yml_scraper.py"

# Rendering needs neither network nor YAML; stub the imports when they are not installed.
for _name in ("requests", "yaml"):
    try:
        __import__(_name)
    except ImportError:
        sys.modules[_name] = types.ModuleType(_name)

_spec = importlib.util.spec_from_file_location("funding_scraper", SCRIPT)
scraper = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scraper)  # main() only runs under __main__

PAYLOAD = "\"'><script>alert(1)</script>"


class RenderTest(unittest.TestCase):
    def render(self, funding=None, **project):
        base = {"project_name": "p", "repo_url": "https://github.com/OWASP/p", "funding_details": ""}
        base["funding_links"] = scraper.funding_links_from_yaml(funding or {})
        return scraper.render_project_item({**base, **project})

    def test_malicious_name_is_escaped(self):
        out = self.render(project_name=PAYLOAD)
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)
        self.assertIn("&quot;&#x27;&gt;", out)

    def test_malicious_funding_values_are_escaped(self):
        out = self.render({"custom": [f"https://example.org/{PAYLOAD}", PAYLOAD], "patreon": PAYLOAD})
        self.assertNotIn("<script>", out)
        self.assertNotIn("'>", out)
        self.assertIn('href="https://example.org/&quot;&#x27;&gt;&lt;script&gt;', out)

    def test_non_http_hrefs_are_rejected(self):
        for bad in ("javascript:alert(1)", "JavaScript:alert(1)", " javascript:alert(1)",
                    "java\tscript:alert(1)", "data:text/html,x", "//evil.example", "OWASP", "vbscript:x"):
            out = self.render({"custom": bad}, repo_url=bad)
            self.assertNotIn("<a ", out, bad)

    def test_platform_handles_become_links(self):
        out = self.render({"github": ["zdresearch"], "patreon": "someone", "open_collective": "proj",
                           "ko_fi": None, "unknown_platform": "x"})
        self.assertIn('href="https://github.com/sponsors/zdresearch"', out)
        self.assertIn('href="https://www.patreon.com/someone"', out)
        self.assertIn('href="https://opencollective.com/proj"', out)
        self.assertNotIn("unknown_platform", out)
        self.assertIn('<a href="https://github.com/OWASP/p">p</a>', out)

    def test_owasp_foundation_links_are_set_apart(self):
        out = self.render({"custom": "https://owasp.org/donate/?x=1&y=2", "github": "OWASP"})
        self.assertIn("No funding link of its own yet.", out)
        self.assertIn('class="foundation"', out)
        self.assertIn('href="https://owasp.org/donate/?x=1&amp;y=2"', out)
        self.assertNotIn('class="fund"', out)

    def test_contributor_sponsors_render(self):
        out = self.render(contributor_sponsors=[{"login": "octocat"}, {"login": PAYLOAD}])
        self.assertIn('href="https://github.com/sponsors/octocat"', out)
        self.assertNotIn("<script>", out)

    def test_page_wraps_items(self):
        page = scraper.render_index_html([{"project_name": PAYLOAD, "repo_url": "", "funding_details": ""}], built="2026-11-06")
        self.assertTrue(page.lstrip().startswith("<!DOCTYPE html>"))
        self.assertIn("owasp.org/donate links no longer reach the project they name", page)
        self.assertIn("&quot;&#x27;&gt;&lt;script&gt;", page)
        self.assertIn("Last built 2026-11-06.", page)
        self.assertNotIn("<script>alert", page)


class Tomato1000Test(unittest.TestCase):
    def profile(self, login, kind=None, target=0, percent=0, sponsors=0):
        goal = {"kind": kind, "targetValue": target, "percentComplete": percent} if kind else None
        return scraper.profile_from_graphql({
            "login": login, "name": login.title(), "hasSponsorsListing": True,
            "sponsors": {"totalCount": sponsors}, "sponsorsListing": {"activeGoal": goal},
        })

    def test_only_a_monthly_dollar_goal_gives_an_amount(self):
        self.assertEqual(self.profile("a", "MONTHLY_SPONSORSHIP_AMOUNT", 2000, 60)["monthly"], 1200)
        self.assertIsNone(self.profile("b", "TOTAL_SPONSORS_COUNT", 25, 40)["monthly"])
        self.assertIsNone(self.profile("c")["monthly"])

    def test_developers_are_ranked_by_progress_and_counted_once(self):
        projects = [{"name": "one", "repo_url": "https://github.com/OWASP/one"},
                    {"name": "two", "repo_url": "https://github.com/OWASP/two"}]
        contributors = {
            "https://github.com/OWASP/one": [{"login": "a", "contributions": 5}, {"login": "x", "contributions": 99}],
            "https://github.com/OWASP/two": [{"login": "a", "contributions": 7}, {"login": "b", "contributions": 1}],
        }
        profiles = {"a": self.profile("a", "TOTAL_SPONSORS_COUNT", 10, 50, 5),
                    "b": self.profile("b", "MONTHLY_SPONSORSHIP_AMOUNT", 1000, 100, 9)}
        data = scraper.build_tomato_1000(projects, contributors, profiles, built="2026-11-06T00:00:00Z")
        self.assertEqual(data["goal"], {"developers": 1000, "monthly_dollars": 1000})
        self.assertEqual(data["contributors_checked"], 3)
        self.assertEqual([d["login"] for d in data["developers"]], ["b", "a"])
        b, a = data["developers"]
        self.assertTrue(b["reached"])
        self.assertEqual(b["progress"], 1.0)
        self.assertFalse(a["reached"])
        self.assertIsNone(a["progress"])
        self.assertEqual(a["contributions"], 12)
        self.assertEqual([p["name"] for p in a["projects"]], ["two", "one"])
        self.assertEqual(a["url"], "https://github.com/sponsors/a")


if __name__ == "__main__":
    unittest.main()
