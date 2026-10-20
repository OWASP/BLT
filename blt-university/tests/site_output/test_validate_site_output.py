import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "validate_site_output", REPO_ROOT / "scripts" / "validate_site_output.py"
)
validate_site_output = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_site_output)


def touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


class ValidateSiteOutputTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.repo = root / "repo"
        self.site = root / "site"

        touch(self.repo / "_courses" / "web-security-intro.md")
        touch(self.repo / "_labs" / "sql_injection.md")
        touch(self.site / "index.html")
        touch(self.site / "courses" / "index.html")
        touch(self.site / "courses" / "web-security-intro" / "index.html")
        touch(self.site / "labs" / "sql_injection" / "index.html")
        touch(self.site / "assets" / "js" / "main.js")

    def problems(self):
        return validate_site_output.find_problems(self.site, self.repo)

    def test_valid_output_has_no_problems(self):
        self.assertEqual(self.problems(), [])

    def test_course_page_without_source_is_reported(self):
        touch(self.site / "courses" / "secure-coding-practices" / "index.html")

        self.assertEqual(
            self.problems(),
            ["courses/secure-coding-practices: no matching _courses/secure-coding-practices.md"],
        )

    def test_lab_page_without_source_is_reported(self):
        touch(self.site / "labs" / "removed_lab" / "index.html")

        self.assertEqual(
            self.problems(),
            ["labs/removed_lab: no matching _labs/removed_lab.md"],
        )

    def test_repository_only_paths_are_reported(self):
        touch(self.site / "package.json")
        touch(self.site / "tests" / "helpers.js")
        touch(self.site / "wrangler.toml")

        self.assertEqual(
            self.problems(),
            [
                "package.json: repository-only path must not be published",
                "tests: repository-only path must not be published",
                "wrangler.toml: repository-only path must not be published",
            ],
        )

    def test_all_forbidden_paths_are_checked(self):
        for name in validate_site_output.FORBIDDEN_PATHS:
            touch(self.site / name / "placeholder")

        self.assertEqual(
            len(self.problems()), len(validate_site_output.FORBIDDEN_PATHS)
        )


if __name__ == "__main__":
    unittest.main()
