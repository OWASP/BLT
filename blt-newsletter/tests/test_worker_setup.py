import re
import unittest
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None


ROOT = Path(__file__).resolve().parents[1]


def load_toml(text):
    if tomllib is not None:
        return tomllib.loads(text)

    config = {}
    current = config
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        if line.startswith("[[") and line.endswith("]]"):
            table_name = line[2:-2].strip()
            parent = config
            parts = table_name.split(".")
            for part in parts[:-1]:
                parent = parent.setdefault(part, {})
            current = {}
            parent.setdefault(parts[-1], []).append(current)
            continue

        if line.startswith("[") and line.endswith("]"):
            table_name = line[1:-1].strip()
            current = config
            for part in table_name.split("."):
                current = current.setdefault(part, {})
            continue

        parts = [part.strip() for part in line.split("=", 1)]
        if len(parts) != 2:
            continue
        key, value = parts
        current[key] = parse_toml_value(value)

    return config


def parse_toml_value(value):
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]

    if value.startswith("[") and value.endswith("]"):
        items = []
        for item in value[1:-1].split(","):
            item = item.strip()
            if item:
                items.append(parse_toml_value(item))
        return items

    if value in {"true", "false"}:
        return value == "true"

    try:
        return int(value)
    except ValueError:
        pass

    try:
        return float(value)
    except ValueError:
        return value


class WorkerSetupTests(unittest.TestCase):
    def test_wrangler_configures_python_worker_with_assets_binding(self):
        config = load_toml((ROOT / "wrangler.toml").read_text())

        self.assertIn("main", config)
        self.assertEqual(config["main"], "src/entry.py")
        self.assertIn("compatibility_flags", config)
        self.assertIn("python_workers", config["compatibility_flags"])
        self.assertIn("disable_python_external_sdk", config["compatibility_flags"])
        self.assertEqual(config["assets"]["directory"], "public")
        self.assertEqual(config["assets"]["binding"], "ASSETS")
        self.assertIn("/api/*", config["assets"]["run_worker_first"])
        self.assertIn("/signup", config["assets"]["run_worker_first"])
        self.assertIn("/signup/", config["assets"]["run_worker_first"])
        self.assertEqual(config["d1_databases"][0]["binding"], "DB")
        self.assertEqual(config["d1_databases"][0]["database_name"], "blt-newsletter")
        self.assertEqual(config["d1_databases"][0]["migrations_dir"], "migrations")
        self.assertIn("queues", config)
        producer = config["queues"]["producers"][0]
        self.assertEqual(producer["binding"], "NEWSLETTER_QUEUE")
        self.assertEqual(producer["queue"], "blt-newsletter-send")

    def test_python_worker_declares_expected_routes(self):
        entrypoint_path = ROOT / "src" / "entry.py"
        self.assertTrue(entrypoint_path.exists())
        entrypoint = entrypoint_path.read_text()

        expected_routes = {
            '"/"': '"index.html"',
            '"/dashboard"': '"dashboard.html"',
            '"/login"': '"login.html"',
            '"/signup"': '"signup.html"',
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
        self.assertIn('onsubmit="login(); return false;"', login_page)
        self.assertIn('type="submit"', login_page)
        self.assertNotIn('id="login-page"', dashboard_page)
        self.assertIn("window.location.href = '/login'", dashboard_page)


if __name__ == "__main__":
    unittest.main()
