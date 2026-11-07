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
        profiles["j"] = self.profile("j", sponsors=2)
        data = scraper.build_tomato_1000(projects, contributors, profiles, joined=["j", "nobody"],
                                         built="2026-11-06T00:00:00Z")
        self.assertEqual(data["goal"], {"developers": 1000, "monthly_dollars": 1000})
        self.assertEqual(data["contributors_checked"], 3)
        self.assertEqual(data["joined"], 2)
        self.assertEqual([d["login"] for d in data["developers"]], ["b", "a", "j"])
        self.assertTrue(data["developers"][2]["joined"])
        self.assertEqual(data["developers"][2]["projects"], [])
        b, a, _ = data["developers"]
        self.assertTrue(b["reached"])
        self.assertEqual(b["progress"], 1.0)
        self.assertFalse(a["reached"])
        self.assertIsNone(a["progress"])
        self.assertEqual(a["contributions"], 12)
        self.assertEqual([p["name"] for p in a["projects"]], ["two", "one"])
        self.assertEqual(a["url"], "https://github.com/sponsors/a")
        self.assertFalse(a["joined"])

    def test_join_list_reads_usernames(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("# comment\n@octocat\n  Someone-Else  # me\nOCTOCAT\nnot a login\n\n")
        self.assertEqual(scraper.read_join_list(f.name), ["octocat", "Someone-Else"])
        self.assertEqual(scraper.read_join_list(f.name + ".missing"), [])
        self.assertEqual(scraper.read_join_list(), [])  # the committed list starts empty

    def test_profile_keeps_top_repositories(self):
        user = {"login": "a", "hasSponsorsListing": True, "sponsors": {"totalCount": 0},
                "repositories": {"nodes": [{"name": "r", "url": "https://github.com/a/r", "stargazerCount": 7}, None]}}
        self.assertEqual(scraper.profile_from_graphql(user)["repos"], [{"name": "r", "url": "https://github.com/a/r", "stars": 7}])


class RateLimitTest(unittest.TestCase):
    class Response:
        def __init__(self, status, remaining=None, reset=None):
            self.status_code = status
            self.headers = {}
            if remaining is not None:
                self.headers["X-RateLimit-Remaining"] = remaining
            if reset is not None:
                self.headers["X-RateLimit-Reset"] = str(reset)

    def test_only_a_spent_limit_waits(self):
        now = scraper.time.time()
        self.assertIsNone(scraper.rate_limit_wait(self.Response(200)))
        self.assertIsNone(scraper.rate_limit_wait(self.Response(403, "12", int(now) + 60)))
        self.assertAlmostEqual(scraper.rate_limit_wait(self.Response(403, "0", int(now) + 60)), 65, delta=2)
        self.assertEqual(scraper.rate_limit_wait(self.Response(429, "0", int(now) - 100)), 5)

    def test_http_waits_once_then_retries(self):
        calls, sleeps = [], []
        responses = [self.Response(403, "0", int(scraper.time.time()) + 30), self.Response(200)]
        # requests may be a stub here (see the top of this file), so restore whatever was there.
        orig_request, orig_sleep = getattr(scraper.requests, "request", None), scraper.time.sleep
        scraper.requests.request = lambda *a, **k: calls.append(a) or responses.pop(0)
        scraper.time.sleep = sleeps.append
        try:
            self.assertEqual(scraper.http("GET", "https://api.github.com/x").status_code, 200)
        finally:
            scraper.requests.request, scraper.time.sleep = orig_request, orig_sleep
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(sleeps), 1)


if __name__ == "__main__":
    unittest.main()
