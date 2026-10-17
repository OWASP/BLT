import os
import stat
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy.sh"


class TestDeployScriptContract(unittest.TestCase):
    def setUp(self):
        self.content = DEPLOY.read_text() if DEPLOY.exists() else ""

    def test_deploy_script_exists_and_is_executable(self):
        self.assertTrue(DEPLOY.is_file(), "deploy.sh must exist at the repository root")
        mode = DEPLOY.stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR, "deploy.sh must be executable by the owner")

    def test_deploy_script_requires_cloudflare_account_id_from_env(self):
        self.assertIn("CLOUDFLARE_ACCOUNT_ID", self.content)
        self.assertIn("CF_ACCOUNT_ID", self.content)
        self.assertIn("Cloudflare account ID", self.content)
        self.assertNotIn("account_id =", self.content)

    def test_deploy_script_verifies_auth_and_deploys_worker(self):
        self.assertIn("npx wrangler whoami", self.content)
        self.assertIn("npx wrangler deploy", self.content)
        self.assertIn("--config wrangler.toml", self.content)
        self.assertIn('"$@"', self.content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
