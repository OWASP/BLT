import re
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkerSetupTests(unittest.TestCase):
    def test_wrangler_configures_python_worker_with_assets_binding(self):
        config = tomllib.loads((ROOT / "wrangler.toml").read_text())

        self.assertIn("main", config)
        self.assertEqual(config["main"], "src/entry.py")
        self.assertIn("compatibility_flags", config)
        self.assertIn("python_workers", config["compatibility_flags"])
        self.assertIn("disable_python_external_sdk", config["compatibility_flags"])
        self.assertEqual(config["assets"]["directory"], "public")
        self.assertEqual(config["assets"]["binding"], "ASSETS")

    def test_python_worker_declares_expected_routes(self):
        entrypoint_path = ROOT / "src" / "entry.py"
        self.assertTrue(entrypoint_path.exists())
        entrypoint = entrypoint_path.read_text()

        expected_routes = {
            '"/"': '"index.html"',
            '"/dashboard"': '"dashboard.html"',
            '"/login"': '"login.html"',
            '"/docs"': '"docs.html"',
        }

        for route, asset in expected_routes.items():
            self.assertRegex(entrypoint, rf"{re.escape(route)}\s*:\s*{re.escape(asset)}")

    def test_login_page_is_separate_from_dashboard(self):
        login_path = ROOT / "public" / "login.html"
        self.assertTrue(login_path.exists())
        login_page = login_path.read_text()
        dashboard_page = (ROOT / "public" / "dashboard.html").read_text()

        self.assertIn('id="login-page"', login_page)
        self.assertIn('onclick="login()"', login_page)
        self.assertNotIn('id="login-page"', dashboard_page)
        self.assertIn("window.location.href = '/login'", dashboard_page)


if __name__ == "__main__":
    unittest.main()
