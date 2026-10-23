import json
import os
import sys
import tempfile
import unittest

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT, "scripts"))
import capture_screenshots  # noqa: E402
import live_sites  # noqa: E402


def write(root, folder, text):
    os.makedirs(os.path.join(root, folder), exist_ok=True)
    with open(os.path.join(root, folder, "wrangler.toml"), "w", encoding="utf-8") as handle:
        handle.write(text)


class LiveSitesTest(unittest.TestCase):
    def test_cloudflare_domains_win_and_prefer_the_folder_name(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, "blt-pool", 'name = "blt-github-app"\nmain = "x.js"\n[vars]\nname = "nope"\n')
            write(root, "blt-home", 'name = "blt-home"\n')
            write(root, "blt-cli", 'name = "blt-cli"\n[[routes]]\npattern = "cli.example.org"\ncustom_domain = true\n')
            write(root, "blt-tool", 'name = "blt-tool"\n')
            domains = {"blt-github-app": ["github-app.example.org", "pool.example.org"],
                       "blt-home": ["www.example.org", "example.org"]}
            urls = live_sites.live_urls(root, ["blt-pool", "blt-home", "blt-cli", "blt-tool"], domains)
        self.assertEqual(urls, {"blt-pool": "https://pool.example.org/", "blt-home": "https://example.org/",
                                "blt-cli": "https://cli.example.org/", "blt-tool": None})

    def test_without_the_api_the_wrangler_routes_are_used(self):
        with tempfile.TemporaryDirectory() as root:
            write(root, "blt-cli", 'name = "blt-cli"\n[[routes]]\npattern = "cli.example.org"\ncustom_domain = true\n')
            self.assertEqual(live_sites.live_urls(root, ["blt-cli"], None), {"blt-cli": "https://cli.example.org/"})


class ScreenshotsTest(unittest.TestCase):
    DATA = {"repos": [{"folder": "b", "live_url": "https://b.example.org/"},
                      {"folder": "a", "live_url": "https://a.example.org/"},
                      {"folder": "c", "live_url": None}]}

    def test_captures_and_keeps_yesterdays_image_for_a_failure(self):
        def shoot(url, token, account):
            if url.startswith("https://b."):
                raise OSError("timeout")
            return b"\xff\xd8jpeg"
        previous = {"b": {"url": "/screenshots/b.jpg", "captured_at": "2026-10-22T07:00:00Z"}}
        with tempfile.TemporaryDirectory() as out:
            payload, captured, failed = capture_screenshots.run(
                self.DATA, "t", "acct", out=out, previous=previous, shoot=shoot, sleep=lambda s: None)
            self.assertEqual(captured, ["a"])
            self.assertEqual(failed, ["b"])
            self.assertEqual(payload["shots"]["b"], previous["b"])
            self.assertEqual(payload["shots"]["a"]["url"], "/screenshots/a.jpg")
            self.assertEqual(sorted(os.listdir(os.path.join(out, "screenshots"))), ["a.jpg", "index.json"])
            with open(os.path.join(out, "screenshots", "index.json"), encoding="utf-8") as handle:
                self.assertEqual(sorted(json.load(handle)["shots"]), ["a", "b"])

    def test_a_rate_limit_waits_and_retries_once(self):
        calls, waits = [], []
        def shoot(url, token, account):
            calls.append(url)
            if len(calls) == 1:
                raise capture_screenshots.RetryLater(5)
            return b"\xff\xd8ok"
        data = {"repos": [{"folder": "a", "live_url": "https://a.example.org/"}]}
        with tempfile.TemporaryDirectory() as out:
            _, captured, _ = capture_screenshots.run(data, "t", "acct", out=out, previous={}, shoot=shoot,
                                                     sleep=waits.append)
        self.assertEqual(captured, ["a"])
        self.assertEqual(waits, [5])


if __name__ == "__main__":
    unittest.main()
