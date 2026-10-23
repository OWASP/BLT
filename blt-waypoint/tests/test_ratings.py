import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT, "scripts"))
import ratings  # noqa: E402

NOW = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
README = "# BLT-Leaf\n\n**Live Site:** https://leaf.owaspblt.org/\n\n" + "x" * 1000 + \
    "\n\n## Run locally\n\n```bash\nnpm test\n```\n\n## Contributing\n\nSee CONTRIBUTING.md.\n"


def write(root, path, text=""):
    full = os.path.join(root, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as handle:
        handle.write(text)


def row(folder, **extra):
    return {"folder": folder, "description": "PR readiness", "live_url": "https://leaf.owaspblt.org",
            "last_commit_at": "2026-10-20T00:00:00Z", "contributor_count": 3, **extra}


class RatingsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.root = self.tmp.name
        write(root, "scripts/ci/tests.tsv", "# project\ttoolchain\tcommand\nblt-leaf\tnode\tnpm test\n")
        write(root, "scripts/deploy/projects.tsv", "# project\tdir\ttype\nblt-leaf\tblt-leaf\tworker\nblt-x\tblt-x\t-\n")
        for name in ("README.md", "LICENSE", "logo.svg", "wrangler.toml"):
            write(root, f"blt-leaf/{name}", README if name == "README.md" else "")
        write(root, "blt-leaf/public/index.html", '<blt-nav project="blt-leaf"></blt-nav>')
        write(root, "blt-x/README.md", "# X\n")
        write(root, "blt-x/wrangler.toml")

    def tearDown(self):
        self.tmp.cleanup()

    def payload(self, *rows, issues=()):
        return ratings.apply({"repos": list(rows), "open_issues": list(issues)}, self.root, NOW)

    def test_gold_when_every_criterion_is_met(self):
        leaf = self.payload(row("blt-leaf"))["repos"][0]
        self.assertEqual(leaf["rating"]["tier"], "gold")
        self.assertEqual(leaf["rating"]["missing"], [])
        self.assertEqual(leaf["rating"]["score"], 100)

    def test_gold_criteria_only_drop_to_silver(self):
        leaf = self.payload(row("blt-leaf", contributor_count=1, last_commit_at="2026-01-01T00:00:00Z"))["repos"][0]
        self.assertEqual(leaf["rating"]["tier"], "silver")
        self.assertEqual(leaf["rating"]["missing"], ["active", "community"])

    def test_stale_issue_fails_triage_and_gold_issue_is_linked(self):
        issues = [{"folder": "blt-leaf", "updated_at": "2026-07-01T00:00:00Z", "html_url": "u1", "labels": []},
                  {"folder": "", "updated_at": "2026-10-22T00:00:00Z", "html_url": "u2",
                   "labels": [{"name": "blt-leaf"}, {"name": "gold-standard"}]}]
        leaf = self.payload(row("blt-leaf"), issues=issues)["repos"][0]
        self.assertEqual(leaf["rating"]["missing"], ["triage"])
        self.assertEqual(leaf["gold_issue"], "u2")

    def test_bronze_and_not_applicable(self):
        data = self.payload(row("blt-x", live_url=None, description=""), row("coderabbit"))
        x, config = data["repos"]
        self.assertEqual(x["rating"]["tier"], "bronze")
        for need in ("readme", "description", "license", "logo", "tests", "deploy", "live", "theme", "setup"):
            self.assertIn(need, x["rating"]["missing"])
        self.assertIsNone(config["rating"])
        self.assertEqual(data["cumulative"]["ratings"], {"bronze": 1, "silver": 0, "gold": 0})
        self.assertEqual({c["id"] for c in data["rating_criteria"]}, {c["id"] for c in ratings.CRITERIA})

    def test_wrangler_in_the_deploy_directory_counts(self):
        os.remove(os.path.join(self.root, "blt-x", "wrangler.toml"))
        write(self.root, "blt-x/cloudflare_workers/wrangler.toml", 'name = "blt-x"\n')
        with open(os.path.join(self.root, "scripts/deploy/projects.tsv"), "a") as handle:
            handle.write("blt-y\tblt-y\tworker\n")
        with open(os.path.join(self.root, "scripts/deploy/projects.tsv")) as handle:
            text = handle.read().replace("blt-x\tblt-x\t-", "blt-x\tblt-x/cloudflare_workers\tworker")
        with open(os.path.join(self.root, "scripts/deploy/projects.tsv"), "w") as handle:
            handle.write(text)
        x = self.payload(row("blt-x", live_url=None))["repos"][0]
        self.assertIn("live", x["rating"]["missing"])
        self.assertNotIn("live", x["rating"]["na"])

    def test_site_criteria_do_not_apply_without_wrangler(self):
        os.remove(os.path.join(self.root, "blt-x", "wrangler.toml"))
        x = self.payload(row("blt-x", live_url=None))["repos"][0]
        self.assertEqual(sorted(x["rating"]["na"]), ["live", "readme_live", "theme"])


if __name__ == "__main__":
    unittest.main()
