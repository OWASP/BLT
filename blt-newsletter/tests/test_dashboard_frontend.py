from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DashboardFrontendTests(unittest.TestCase):
    def test_dashboard_does_not_include_dark_mode_controls(self):
        dashboard_html = (ROOT / "public" / "dashboard.html").read_text()

        self.assertNotIn("toggleTheme", dashboard_html)
        self.assertNotIn("html.dark", dashboard_html)
        self.assertNotIn("classList.toggle('dark')", dashboard_html)
        self.assertNotIn("fa-moon", dashboard_html)
        self.assertNotIn("--background-dark", dashboard_html)


if __name__ == "__main__":
    unittest.main()
