import importlib
import sys
import types
import unittest
from unittest import mock


class WorkerLogRouteContractTests(unittest.TestCase):
    def load_worker_with_fakes(self):
        class FakeResponse:
            def __init__(self, body, status=200, headers=None):
                self.body = body
                self.status = status
                self.headers = headers or {}

        fake_workers = types.ModuleType("workers")
        setattr(fake_workers, "Response", FakeResponse)

        original_worker = sys.modules.pop("src.worker", None)
        try:
            with mock.patch.dict(sys.modules, {"workers": fake_workers}):
                return importlib.import_module("src.worker")
        finally:
            sys.modules.pop("src.worker", None)
            if original_worker is not None:
                sys.modules["src.worker"] = original_worker

    def test_worker_declares_work_log_stats_and_export_routes(self):
        worker = self.load_worker_with_fakes()
        route_text = repr(worker._ROUTES)

        for route in [
            "/api/logs",
            "/api/logs/(?P<sid>[^/]+)",
            "/api/stats",
            "/api/export",
        ]:
            self.assertIn(route, route_text)

        for handler_name in [
            "handle_create_log",
            "handle_list_logs",
            "handle_get_log",
            "handle_update_log",
            "handle_delete_log",
            "handle_stats",
            "handle_export_csv",
            "handle_export_json",
        ]:
            self.assertTrue(hasattr(worker, handler_name), handler_name)

    def test_cors_allows_patch_for_log_updates(self):
        worker = self.load_worker_with_fakes()

        self.assertIn("PATCH", worker._CORS_HEADERS["Access-Control-Allow-Methods"])


if __name__ == "__main__":
    unittest.main()
