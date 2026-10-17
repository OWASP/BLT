import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "migrate.sh"
PACKAGE = ROOT / "package.json"
README = ROOT / "README.md"


class TestMigrateScriptContract(unittest.TestCase):
    def test_dev_prod_migration_script_exists_and_has_safety_guards(self):
        self.assertTrue(SCRIPT.is_file())
        source = SCRIPT.read_text()
        self.assertIn("set -euo pipefail", source)
        self.assertIn("dev|development|local", source)
        self.assertIn("prod|production|remote", source)
        self.assertIn("--local", source)
        self.assertIn("--remote", source)
        self.assertIn("CONFIRM_PROD_MIGRATION", source)
        self.assertIn("D1_DATABASE", source)
        self.assertIn("npx wrangler d1 migrations apply", source)

    def test_package_json_exposes_dev_and_prod_migration_scripts(self):
        package = json.loads(PACKAGE.read_text())
        scripts = package.get("scripts", {})
        self.assertEqual("bash scripts/migrate.sh dev", scripts.get("db:migrate:dev"))
        self.assertEqual("bash scripts/migrate.sh prod", scripts.get("db:migrate:prod"))
        self.assertNotIn("schema.sql", scripts.get("db:init", ""))

    def test_readme_documents_current_env_migrations_and_smoke_flow(self):
        readme = README.read_text()
        for text in [
            "npm run db:migrate:dev",
            "npm run db:migrate:prod",
            "CONFIRM_PROD_MIGRATION=1",
            "EMAIL_API_KEY",
            "OTP_SECRET",
            "SESSION_SECRET",
            "ENCRYPTION_KEY",
            "SendGrid",
            "Create an account",
            "Verify email",
            "Create organization",
            "Submit a check-in",
        ]:
            self.assertIn(text, readme)
        self.assertNotIn("KV namespace", readme)
        self.assertNotIn("Login with GitHub", readme)
    def test_readme_documents_security_limitations_for_encryption(self):
        readme = README.read_text()
        self.assertIn("base64 placeholder", readme)
        self.assertIn("AES-GCM", readme)
        self.assertIn("encrypted field strategy", readme)


if __name__ == "__main__":
    unittest.main(verbosity=2)
