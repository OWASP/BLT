import importlib
import sys
import types
import unittest
from unittest import mock


class WorkerFrontendRouteTests(unittest.TestCase):
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

    def test_root_redirects_to_static_landing_page(self):
        worker = self.load_worker_with_fakes()

        response = worker.handle_root()

        self.assertEqual(response.status, 302)
        self.assertEqual(response.headers["Location"], "/index.html")


if __name__ == "__main__":
    unittest.main()
