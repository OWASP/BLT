import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = ROOT / ".env.example"


class TestEnvExampleContract(unittest.TestCase):
    def setUp(self):
        self.content = ENV_EXAMPLE.read_text()

    def test_env_example_only_contains_relevant_refactor_envs(self):
        expected = [
            "APP_NAME=",
            "APP_URL=",
            "WORKER_HOST=",
            "ENCRYPTION_KEY=",
            "OTP_SECRET=",
            "SESSION_SECRET=",
            "EMAIL_PROVIDER=",
            "EMAIL_API_KEY=",
            "EMAIL_FROM=",
            "EMAIL_FROM_NAME=",
            "DEFAULT_TIMEZONE=",
            "DEBUG=",
        ]
        for key in expected:
            self.assertIn(key, self.content)

        irrelevant = ["MAILGUN", "AWS_", "KV_NAMESPACE", "DEFAULT_SLACK_WEBHOOK", "D1_DATABASE_ID"]
        for key in irrelevant:
            self.assertNotIn(key, self.content)

    def test_env_example_mentions_production_secret_commands_and_generation(self):
        self.assertIn("wrangler secret put ENCRYPTION_KEY", self.content)
        self.assertIn("wrangler secret put OTP_SECRET", self.content)
        self.assertIn("wrangler secret put SESSION_SECRET", self.content)
        self.assertIn("wrangler secret put EMAIL_API_KEY", self.content)
        self.assertIn("openssl rand -base64 32", self.content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
