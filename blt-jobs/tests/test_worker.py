"""Read-time expiry of /data/jobs.json (src/worker.py). Run: npm run test:worker"""
import asyncio
import json
import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import worker  # noqa: E402

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
DATA = {
    "jobs": [
        {"id": "future", "effective_expires_at": "2026-10-19T00:00:00.000Z"},
        {"id": "past", "effective_expires_at": "2026-10-18T11:59:59.000Z"},
        {"id": "exact", "effective_expires_at": "2026-10-18T12:00:00.000Z"},
        {"id": "no-expiry", "effective_expires_at": None},
        {"id": "unparsable", "effective_expires_at": "soon"},
    ],
    "count": 5,
    "source": {"provider": {"id": "forge"}},
}


class FakeAsset:
    def __init__(self, status, body):
        self.status, self.body = status, body

    async def text(self):
        return self.body


class FakeAssets:
    def __init__(self, asset):
        self.asset, self.urls = asset, []

    async def fetch(self, url):
        self.urls.append(url)
        return self.asset


class FakeEnv:
    def __init__(self, asset):
        self.ASSETS = FakeAssets(asset)


class DropExpiredJobsTest(unittest.TestCase):
    def test_drops_expired_and_fixes_count(self):
        out = worker.drop_expired_jobs(DATA, now=NOW)
        self.assertEqual([j["id"] for j in out["jobs"]], ["future", "no-expiry", "unparsable"])
        self.assertEqual(out["count"], 3)
        self.assertEqual(out["source"], DATA["source"])
        self.assertEqual(DATA["count"], 5)  # input not mutated

    def test_passes_through_unexpected_shapes(self):
        self.assertEqual(worker.drop_expired_jobs({"seekers": []}, now=NOW), {"seekers": []})
        self.assertEqual(worker.drop_expired_jobs([], now=NOW), [])

    def test_naive_timestamp_is_utc(self):
        out = worker.drop_expired_jobs({"jobs": [{"effective_expires_at": "2026-10-18T11:00:00"}]}, now=NOW)
        self.assertEqual(out["count"], 0)


class ServeActiveJobsTest(unittest.TestCase):
    def test_serves_filtered_json_with_short_cache(self):
        env = FakeEnv(FakeAsset(200, json.dumps({"jobs": [{"id": "old", "effective_expires_at": "2000-01-01T00:00:00Z"}], "count": 1})))
        response = asyncio.run(worker.serve_active_jobs(env))
        self.assertEqual(env.ASSETS.urls, ["https://assets.local/data/jobs.json"])
        self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(response.body), {"jobs": [], "count": 0})
        self.assertEqual(response.headers["Cache-Control"], "public, max-age=300")

    def test_missing_asset_is_returned_as_is(self):
        asset = FakeAsset(404, "Not found")
        self.assertIs(asyncio.run(worker.serve_active_jobs(FakeEnv(asset))), asset)


class SessionSecretTest(unittest.TestCase):
    class Request:
        def __init__(self, cookie):
            self.headers = {"Cookie": cookie}

    class Env:
        pass

    def forged_cookie(self, secret):
        payload = worker.base64_url_encode(json.dumps({"exp": 4102444800}).encode())
        return f"{worker.SESSION_COOKIE}={payload}.{worker.sign(payload, secret)}"

    def test_no_secret_means_no_valid_session(self):
        request = self.Request(self.forged_cookie("unset-admin-secret"))
        self.assertFalse(worker.is_authenticated(request, self.Env()))

    def test_cookie_signed_with_the_configured_secret_is_accepted(self):
        env = self.Env()
        env.ADMIN_SESSION_SECRET = "s3cret"
        self.assertTrue(worker.is_authenticated(self.Request(self.forged_cookie("s3cret")), env))
        self.assertFalse(worker.is_authenticated(self.Request(self.forged_cookie("other")), env))


if __name__ == "__main__":
    unittest.main()
