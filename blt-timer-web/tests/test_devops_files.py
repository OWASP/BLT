from pathlib import Path
import stat
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATE = ROOT / "migrate.sh"
ENV_EXAMPLE = ROOT / ".env.example"
DEPLOY = ROOT / "deploy.sh"


class DevopsFileTests(unittest.TestCase):
    def test_migrate_script_supports_dev_and_prod_d1_targets(self):
        self.assertTrue(MIGRATE.exists(), "migrate.sh must exist")
        content = MIGRATE.read_text()

        self.assertIn("Usage:", content)
        self.assertIn("dev|prod", content)
        self.assertIn("npx wrangler d1 migrations apply DB --local", content)
        self.assertIn("npx wrangler d1 migrations apply DB --remote --env production", content)
        self.assertIn("set -euo pipefail", content)
        self.assertNotIn("github", content.lower())
        self.assertNotIn("gitlab", content.lower())

    def test_migrate_script_is_executable(self):
        self.assertTrue(MIGRATE.exists(), "migrate.sh must exist")
        mode = MIGRATE.stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR, "migrate.sh should be executable by the owner")

    def test_migrate_script_accepts_an_isolated_local_d1_directory(self):
        content = MIGRATE.read_text()

        self.assertIn("BLT_D1_PERSIST_TO", content)
        self.assertIn("--persist-to", content)

    def test_wrangler_uses_blt_timer_production_name(self):
        config = (ROOT / "wrangler.toml").read_text()

        self.assertIn('name = "blt-timer-production"', config)
        self.assertNotIn("fresh-time-tracker-prod", config)

    def test_deploy_script_runs_migration_before_production_deploy(self):
        self.assertTrue(DEPLOY.exists(), "deploy.sh must exist")
        content = DEPLOY.read_text()

        self.assertIn("set -euo pipefail", content)
        self.assertIn("./migrate.sh prod", content)
        self.assertIn("npx wrangler deploy --env production", content)
        self.assertLess(
            content.index("./migrate.sh prod"),
            content.index("npx wrangler deploy --env production"),
        )

    def test_deploy_script_is_executable_and_supports_dry_run(self):
        self.assertTrue(DEPLOY.exists(), "deploy.sh must exist")
        self.assertTrue(DEPLOY.stat().st_mode & stat.S_IXUSR)
        content = DEPLOY.read_text()

        self.assertIn("--dry-run", content)
        self.assertIn("DRY RUN:", content)

    def test_env_example_contains_only_relevant_blt_timer_values(self):
        self.assertTrue(ENV_EXAMPLE.exists(), ".env.example must exist")
        content = ENV_EXAMPLE.read_text()

        self.assertIn("SESSION_SECRET=", content)
        self.assertIn("APP_BASE_URL=http://localhost:8787", content)
        self.assertIn("APP_ENV=development", content)
        self.assertIn("BLT Timer Web", content)

        removed_values = [
            "GITHUB_CLIENT_ID",
            "GITHUB_CLIENT_SECRET",
            "GITLAB",
            "LOCAL_LLM_ENDPOINT",
            "ENCRYPTION_KEY",
            "SENDGRID",
            "OPENAI",
        ]
        for value in removed_values:
            self.assertNotIn(value, content)


if __name__ == "__main__":
    unittest.main()
