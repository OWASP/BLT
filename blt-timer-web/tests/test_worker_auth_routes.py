import importlib
import sys
import types
import unittest
from unittest import mock


class WorkerAuthRouteContractTests(unittest.TestCase):
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

    def test_worker_declares_custom_auth_routes(self):
        worker = self.load_worker_with_fakes()
        route_text = repr(worker._ROUTES)

        for route in [
            "/api/auth/register",
            "/api/auth/login",
            "/api/auth/logout",
            "/api/me",
        ]:
            self.assertIn(route, route_text)

        for handler_name in [
            "handle_register",
            "handle_login",
            "handle_logout",
            "handle_me",
            "get_current_user",
        ]:
            self.assertTrue(hasattr(worker, handler_name), handler_name)

    def test_json_response_helpers_can_attach_set_cookie_header(self):
        worker = self.load_worker_with_fakes()

        response = worker.json_ok({"ok": True}, headers={"Set-Cookie": "blt_timer_session=abc"})

        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers["Set-Cookie"], "blt_timer_session=abc")
        self.assertEqual(response.headers["Content-Type"], "application/json")

    def test_worker_declares_profile_update_route(self):
        worker = self.load_worker_with_fakes()

        self.assertIn("PATCH", repr(worker._ROUTES))
        self.assertIn("/api/me", repr(worker._ROUTES))
        self.assertTrue(hasattr(worker, "handle_update_me"))
        self.assertTrue(hasattr(worker, "_normalize_profile_payload"))

    def test_profile_payload_requires_a_valid_name_and_timezone(self):
        worker = self.load_worker_with_fakes()

        self.assertEqual(
            worker._normalize_profile_payload(
                {"displayName": "Aisha Khan", "timezone": "Asia/Kolkata"}
            ),
            {"display_name": "Aisha Khan", "timezone": "Asia/Kolkata"},
        )
        self.assertTrue(hasattr(worker, "_normalize_timezone"))
        self.assertEqual(worker._normalize_timezone("Pacific/Auckland"), "Pacific/Auckland")
        self.assertEqual(worker._normalize_timezone(None), "UTC")

        for payload in [
            {"displayName": "", "timezone": "UTC"},
            {"displayName": "Aisha", "timezone": "not a timezone"},
            {"displayName": "A" * 81, "timezone": "UTC"},
        ]:
            with self.assertRaises(ValueError):
                worker._normalize_profile_payload(payload)

        with self.assertRaises(ValueError):
            worker._normalize_timezone("not a timezone")


if __name__ == "__main__":
    unittest.main()
