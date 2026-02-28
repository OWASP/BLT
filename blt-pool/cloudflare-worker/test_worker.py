"""Unit tests for pure-Python utility functions in worker.py.

These tests cover the logic that does NOT require the Cloudflare runtime
(no ``from js import ...`` needed).  Run with:

    pip install pytest
    pytest cloudflare-worker/test_worker.py -v
"""

import base64
import hashlib
import hmac as _hmac
import importlib
import json
import sys
import types
import unittest

# ---------------------------------------------------------------------------
# Minimal stub for the ``js`` module so worker.py can be imported outside the
# Cloudflare runtime.
# ---------------------------------------------------------------------------

_js_stub = types.ModuleType("js")


class _HeadersStub:
    def __init__(self, items=None):
        self._data = dict(items or [])

    @classmethod
    def new(cls, items):
        return cls(items)

    def get(self, key, default=None):
        return self._data.get(key, default)


class _ResponseStub:
    def __init__(self, body="", status=200, headers=None):
        self.body = body
        self.status = status
        self.headers = headers or _HeadersStub()

    @classmethod
    def new(cls, body="", status=200, headers=None):
        return cls(body, status, headers)


_js_stub.Headers = _HeadersStub
_js_stub.Response = _ResponseStub
_js_stub.console = types.SimpleNamespace(error=print, log=print)
_js_stub.fetch = None  # not used in unit tests

sys.modules.setdefault("js", _js_stub)

# Now import the worker module
import importlib.util
import pathlib

_worker_path = pathlib.Path(__file__).parent / "worker.py"
_spec = importlib.util.spec_from_file_location("worker", _worker_path)
_worker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_worker)


# ---------------------------------------------------------------------------
# Helpers re-exported for convenience
# ---------------------------------------------------------------------------

verify_signature = _worker.verify_signature
pem_to_pkcs8_der = _worker.pem_to_pkcs8_der
_wrap_pkcs1_as_pkcs8 = _worker._wrap_pkcs1_as_pkcs8
_der_len = _worker._der_len
_b64url = _worker._b64url
_is_human = _worker._is_human


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestB64url(unittest.TestCase):
    def test_no_padding(self):
        result = _b64url(b"hello world")
        self.assertNotIn("=", result)

    def test_known_value(self):
        # base64url of b"\xfb\xff\xfe" is "-__-" (url-safe, no padding)
        self.assertEqual(_b64url(b"\xfb\xff\xfe"), "-__-")

    def test_empty(self):
        self.assertEqual(_b64url(b""), "")


class TestVerifySignature(unittest.TestCase):
    def _make_sig(self, payload: bytes, secret: str) -> str:
        return "sha256=" + _hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()

    def test_valid_signature(self):
        payload = b'{"action":"opened"}'
        secret = "mysecret"
        sig = self._make_sig(payload, secret)
        self.assertTrue(verify_signature(payload, sig, secret))

    def test_wrong_payload(self):
        secret = "mysecret"
        sig = self._make_sig(b"original", secret)
        self.assertFalse(verify_signature(b"tampered", sig, secret))

    def test_wrong_secret(self):
        payload = b'{"action":"opened"}'
        sig = self._make_sig(payload, "correct")
        self.assertFalse(verify_signature(payload, sig, "wrong"))

    def test_missing_prefix(self):
        payload = b"data"
        bare_hex = _hmac.new(b"s", payload, hashlib.sha256).hexdigest()
        self.assertFalse(verify_signature(payload, bare_hex, "s"))

    def test_empty_signature(self):
        self.assertFalse(verify_signature(b"data", "", "secret"))

    def test_none_signature(self):
        self.assertFalse(verify_signature(b"data", None, "secret"))


class TestDerLen(unittest.TestCase):
    def test_small(self):
        self.assertEqual(_der_len(0), bytes([0]))
        self.assertEqual(_der_len(127), bytes([127]))

    def test_one_byte_extended(self):
        self.assertEqual(_der_len(128), bytes([0x81, 128]))
        self.assertEqual(_der_len(255), bytes([0x81, 255]))

    def test_two_byte_extended(self):
        result = _der_len(256)
        self.assertEqual(result, bytes([0x82, 1, 0]))
        result2 = _der_len(0x1234)
        self.assertEqual(result2, bytes([0x82, 0x12, 0x34]))


class TestWrapPkcs1AsPkcs8(unittest.TestCase):
    def test_output_starts_with_sequence_tag(self):
        dummy_pkcs1 = b"\x30" + bytes(10)
        result = _wrap_pkcs1_as_pkcs8(dummy_pkcs1)
        # Outer tag must be 0x30 (SEQUENCE)
        self.assertEqual(result[0], 0x30)

    def test_contains_rsa_oid(self):
        dummy_pkcs1 = bytes(20)
        result = _wrap_pkcs1_as_pkcs8(dummy_pkcs1)
        # RSA OID bytes should be present in the wrapper
        rsa_oid = bytes([0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x01, 0x01])
        self.assertIn(rsa_oid, result)

    def test_pkcs1_content_present(self):
        pkcs1_data = b"\xAB\xCD\xEF"
        result = _wrap_pkcs1_as_pkcs8(pkcs1_data)
        self.assertIn(pkcs1_data, result)


class TestPemToPkcs8Der(unittest.TestCase):
    def _make_pkcs8_pem(self, payload: bytes) -> str:
        b64 = base64.b64encode(payload).decode()
        return f"-----BEGIN PRIVATE KEY-----\n{b64}\n-----END PRIVATE KEY-----"

    def _make_pkcs1_pem(self, payload: bytes) -> str:
        b64 = base64.b64encode(payload).decode()
        return f"-----BEGIN RSA PRIVATE KEY-----\n{b64}\n-----END RSA PRIVATE KEY-----"

    def test_pkcs8_passthrough(self):
        data = b"\x01\x02\x03"
        pem = self._make_pkcs8_pem(data)
        result = pem_to_pkcs8_der(pem)
        self.assertEqual(result, data)

    def test_pkcs1_wraps(self):
        data = bytes(20)
        pem = self._make_pkcs1_pem(data)
        result = pem_to_pkcs8_der(pem)
        # Result is a PKCS#8 wrapper (longer than original, starts with SEQUENCE)
        self.assertGreater(len(result), len(data))
        self.assertEqual(result[0], 0x30)
        self.assertIn(data, result)

    def test_strips_pem_headers(self):
        data = b"\xDE\xAD\xBE\xEF"
        pem = self._make_pkcs8_pem(data)
        result = pem_to_pkcs8_der(pem)
        # Should not contain literal "PRIVATE KEY" bytes
        self.assertNotIn(b"PRIVATE KEY", result)


class TestIsHuman(unittest.TestCase):
    def test_user_type(self):
        self.assertTrue(_is_human({"type": "User", "login": "alice"}))

    def test_mannequin_type(self):
        self.assertTrue(_is_human({"type": "Mannequin", "login": "m1"}))

    def test_bot_type(self):
        self.assertFalse(_is_human({"type": "Bot", "login": "dependabot"}))

    def test_app_type(self):
        self.assertFalse(_is_human({"type": "App", "login": "some-app"}))

    def test_none(self):
        self.assertFalse(_is_human(None))

    def test_empty_dict(self):
        self.assertFalse(_is_human({}))


if __name__ == "__main__":
    unittest.main()
