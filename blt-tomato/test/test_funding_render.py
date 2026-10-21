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
    def render(self, **project):
        base = {"project_name": "p", "repo_url": "https://github.com/OWASP/p", "funding_details": ""}
        return scraper.render_project_item(1, {**base, **project})

    def test_malicious_name_is_escaped(self):
        out = self.render(project_name=PAYLOAD)
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)
        self.assertIn("&quot;&#x27;&gt;", out)

    def test_malicious_funding_values_are_escaped(self):
        out = self.render(funding_details=f"https://example.org/{PAYLOAD}, {PAYLOAD}")
        self.assertNotIn("<script>", out)
        self.assertNotIn("'>", out)
        self.assertIn('href="https://example.org/&quot;&#x27;&gt;&lt;script&gt;', out)

    def test_non_http_hrefs_are_rejected(self):
        for bad in ("javascript:alert(1)", "JavaScript:alert(1)", " javascript:alert(1)",
                    "java\tscript:alert(1)", "data:text/html,x", "//evil.example", "OWASP", "vbscript:x"):
            out = self.render(funding_details=bad, repo_url=bad)
            self.assertNotIn("<a ", out, bad)

    def test_http_links_still_render(self):
        out = self.render(funding_details="https://owasp.org/donate/?x=1&y=2, https://opencollective.com/p")
        self.assertIn('<a href="https://owasp.org/donate/?x=1&amp;y=2" class="donate-button">Donate</a>', out)
        self.assertIn('<a href="https://opencollective.com/p" class="heart-icon">', out)
        self.assertIn('<a href="https://github.com/OWASP/p">p</a>', out)

    def test_page_wraps_items(self):
        page = scraper.render_index_html([{"project_name": PAYLOAD, "repo_url": "", "funding_details": ""}])
        self.assertTrue(page.lstrip().startswith("<!DOCTYPE html>"))
        self.assertIn("<li>1. &quot;", page)
        self.assertNotIn("<script>", page)


if __name__ == "__main__":
    unittest.main()
