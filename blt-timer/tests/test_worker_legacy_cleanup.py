import importlib
import sys
import types
import unittest
from unittest import mock


class WorkerLegacyCleanupTests(unittest.TestCase):
    def load_worker_with_fakes(self):
        class FakeResponse:
            def __init__(self, body, status=200, headers=None):
                self.body = body
                self.status = status
                self.headers = headers or {}

        fake_workers = types.ModuleType("workers")
        fake_workers.Response = FakeResponse
        original_worker = sys.modules.pop("src.worker", None)
        try:
            with mock.patch.dict(sys.modules, {"workers": fake_workers}):
                return importlib.import_module("src.worker")
        finally:
            sys.modules.pop("src.worker", None)
            if original_worker is not None:
                sys.modules["src.worker"] = original_worker

    def test_retired_routes_handlers_and_identity_headers_are_absent(self):
        worker = self.load_worker_with_fakes()
        routes = repr(worker._ROUTES)

        for retired_path in [
            "/api/sessions",
            "/api/activity",
            "/api/webhooks/github",
        ]:
            self.assertNotIn(retired_path, routes)

        for retired_handler in [
            "handle_start_session",
            "handle_end_session",
            "handle_pause_session",
            "handle_resume_session",
            "handle_get_session",
            "handle_list_sessions",
            "handle_track_activity",
            "handle_get_activities",
            "handle_get_summary",
            "handle_github_webhook",
            "_parse_github_webhook",
        ]:
            self.assertFalse(hasattr(worker, retired_handler), retired_handler)

        self.assertNotIn("X-User-ID", worker._CORS_HEADERS["Access-Control-Allow-Headers"])
        self.assertNotIn("X-Session-ID", worker._CORS_HEADERS["Access-Control-Allow-Headers"])


if __name__ == "__main__":
    unittest.main()
