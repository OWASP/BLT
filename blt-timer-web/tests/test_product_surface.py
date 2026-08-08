from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCS = [
    ROOT / "README.md",
    ROOT / "docs" / "README.md",
    ROOT / "docs" / "SETUP.md",
    ROOT / "docs" / "PRIVACY.md",
]


class ProductSurfaceTests(unittest.TestCase):
    def test_retired_examples_and_summary_are_removed(self):
        for retired_path in [
            ROOT / "examples" / "cli_tracker.py",
            ROOT / "examples" / "github_integration.py",
            ROOT / "IMPLEMENTATION_SUMMARY.md",
        ]:
            self.assertFalse(retired_path.exists(), retired_path)

    def test_documentation_describes_only_manual_timer_product(self):
        for path in DOCS:
            content = path.read_text().lower()
            self.assertIn("blt timer", content, path)
            self.assertNotIn("/api/sessions", content, path)
            self.assertNotIn("/api/activity", content, path)
            self.assertNotIn("/api/webhooks/github", content, path)
            self.assertNotIn("local_llm_endpoint", content, path)
            self.assertNotIn("github oauth", content, path)

    def test_setup_documents_cookie_auth_and_clean_d1_migration(self):
        content = (ROOT / "docs" / "SETUP.md").read_text()
        self.assertIn("SESSION_SECRET", content)
        self.assertIn("./migrate.sh dev", content)
        self.assertIn("npx wrangler dev", content)
        self.assertIn("work logs", content.lower())


if __name__ == "__main__":
    unittest.main()
