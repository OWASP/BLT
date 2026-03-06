"""Unit tests for pure-Python utility functions and event handlers in worker.py.

These tests cover the logic that does NOT require the Cloudflare runtime
(no ``from js import ...`` needed).  Run with:

    pip install pytest
    pytest test_worker.py -v
"""

import asyncio
import base64
import hashlib
import hmac as _hmac
import importlib
import json
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Minimal stub for the ``js`` module so worker.py can be imported outside the
# Cloudflare runtime.
# ---------------------------------------------------------------------------

_js_stub = types.ModuleType("js")

# Stub for pyodide.ffi — makes to_js a transparent pass-through outside runtime
_pyodide_ffi_stub = types.ModuleType("pyodide.ffi")
_pyodide_ffi_stub.to_js = lambda x, **kw: x
_pyodide_stub = types.ModuleType("pyodide")
_pyodide_stub.ffi = _pyodide_ffi_stub
sys.modules.setdefault("pyodide", _pyodide_stub)
sys.modules.setdefault("pyodide.ffi", _pyodide_ffi_stub)


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

_worker_path = pathlib.Path(__file__).parent / "src" / "worker.py"
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


# ---------------------------------------------------------------------------
# Handler tests — mirror the Node.js Jest test suite
# ---------------------------------------------------------------------------

def _run(coro):
    """Run a coroutine synchronously."""
    return asyncio.run(coro)


def _make_issue_payload(
    owner="OWASP-BLT",
    repo="TestRepo",
    number=1,
    state="open",
    assignees=None,
    labels=None,
    html_url="https://github.com/OWASP-BLT/TestRepo/issues/1",
    title="Test issue",
    is_pr=False,
    comment_body="/assign",
    comment_user=None,
    sender=None,
    label=None,
):
    if assignees is None:
        assignees = []
    if labels is None:
        labels = []
    if comment_user is None:
        comment_user = {"login": "alice", "type": "User"}
    if sender is None:
        sender = {"login": "alice", "type": "User"}
    issue = {
        "number": number,
        "state": state,
        "assignees": assignees,
        "labels": labels,
        "html_url": html_url,
        "title": title,
    }
    if is_pr:
        issue["pull_request"] = {"url": "https://api.github.com/repos/test/test/pulls/1"}
    payload = {
        "repository": {"owner": {"login": owner}, "name": repo},
        "issue": issue,
        "comment": {"user": comment_user, "body": comment_body},
        "sender": sender,
    }
    if label is not None:
        payload["label"] = label
    return payload


def _make_pr_payload(
    owner="OWASP-BLT",
    repo="TestRepo",
    number=1,
    merged=False,
    pr_user=None,
    sender=None,
):
    if pr_user is None:
        pr_user = {"login": "alice", "type": "User"}
    if sender is None:
        sender = {"login": "alice", "type": "User"}
    return {
        "repository": {"owner": {"login": owner}, "name": repo},
        "pull_request": {"number": number, "merged": merged, "user": pr_user},
        "sender": sender,
    }


class TestHandleAssign(unittest.TestCase):
    """_assign — mirrors handleAssign in issue-assign.test.js"""

    def _run_assign(self, payload, comments, github_calls):
        async def _inner():
            with (
                patch.object(_worker, "create_comment", new=AsyncMock(side_effect=lambda o, r, n, b, t: comments.append(b))),
                patch.object(_worker, "github_api", new=AsyncMock(side_effect=lambda *a, **kw: github_calls.append(a))),
            ):
                await _worker._assign(
                    payload["repository"]["owner"]["login"],
                    payload["repository"]["name"],
                    payload["issue"],
                    payload["comment"]["user"]["login"],
                    "tok",
                )
        _run(_inner())

    def test_assigns_user_to_open_issue(self):
        payload = _make_issue_payload()
        comments, calls = [], []
        self._run_assign(payload, comments, calls)
        # Expect a POST to the assignees endpoint
        self.assertTrue(any(
            method == "POST" and "assignees" in path
            for method, path, *_ in calls
        ))
        self.assertTrue(any("assigned to this issue" in c for c in comments))

    def test_does_not_assign_closed_issue(self):
        payload = _make_issue_payload(state="closed")
        comments, calls = [], []
        self._run_assign(payload, comments, calls)
        self.assertEqual(calls, [])
        self.assertTrue(any("already closed" in c for c in comments))

    def test_does_not_assign_already_assigned(self):
        payload = _make_issue_payload(assignees=[{"login": "alice"}])
        comments, calls = [], []
        self._run_assign(payload, comments, calls)
        self.assertEqual(calls, [])
        self.assertTrue(any("already assigned" in c for c in comments))

    def test_does_not_assign_when_max_assignees_reached(self):
        payload = _make_issue_payload(
            assignees=[{"login": "bob"}, {"login": "carol"}, {"login": "dave"}]
        )
        comments, calls = [], []
        self._run_assign(payload, comments, calls)
        self.assertEqual(calls, [])
        self.assertTrue(any("maximum number of assignees" in c for c in comments))

    def test_does_not_assign_on_pull_request(self):
        payload = _make_issue_payload(is_pr=True)
        comments, calls = [], []
        self._run_assign(payload, comments, calls)
        self.assertEqual(calls, [])
        self.assertTrue(any("pull requests" in c for c in comments))


class TestHandleUnassign(unittest.TestCase):
    """_unassign — mirrors handleUnassign in issue-assign.test.js"""

    def _run_unassign(self, payload, comments, github_calls):
        async def _inner():
            with (
                patch.object(_worker, "create_comment", new=AsyncMock(side_effect=lambda o, r, n, b, t: comments.append(b))),
                patch.object(_worker, "github_api", new=AsyncMock(side_effect=lambda *a, **kw: github_calls.append(a))),
            ):
                await _worker._unassign(
                    payload["repository"]["owner"]["login"],
                    payload["repository"]["name"],
                    payload["issue"],
                    payload["comment"]["user"]["login"],
                    "tok",
                )
        _run(_inner())

    def test_removes_user_from_assigned_issue(self):
        payload = _make_issue_payload(assignees=[{"login": "alice"}])
        comments, calls = [], []
        self._run_unassign(payload, comments, calls)
        # Expect a DELETE to the assignees endpoint
        self.assertTrue(any(
            method == "DELETE" and "assignees" in path
            for method, path, *_ in calls
        ))
        self.assertTrue(any("unassigned" in c for c in comments))

    def test_does_not_remove_user_not_assigned(self):
        payload = _make_issue_payload(assignees=[])
        comments, calls = [], []
        self._run_unassign(payload, comments, calls)
        self.assertEqual(calls, [])
        self.assertTrue(any("not currently assigned" in c for c in comments))


class TestHandleIssueComment(unittest.TestCase):
    """handle_issue_comment — routes /assign and /unassign commands"""

    def _run_comment(self, payload, assign_calls, unassign_calls):
        async def _inner():
            with (
                patch.object(_worker, "_assign", new=AsyncMock(side_effect=lambda *a: assign_calls.append(a))),
                patch.object(_worker, "_unassign", new=AsyncMock(side_effect=lambda *a: unassign_calls.append(a))),
            ):
                await _worker.handle_issue_comment(payload, "tok")
        _run(_inner())

    def test_routes_assign_command(self):
        payload = _make_issue_payload(comment_body="/assign")
        assigns, unassigns = [], []
        self._run_comment(payload, assigns, unassigns)
        self.assertEqual(len(assigns), 1)
        self.assertEqual(len(unassigns), 0)

    def test_routes_unassign_command(self):
        payload = _make_issue_payload(comment_body="/unassign")
        assigns, unassigns = [], []
        self._run_comment(payload, assigns, unassigns)
        self.assertEqual(len(assigns), 0)
        self.assertEqual(len(unassigns), 1)

    def test_ignores_bot_comments(self):
        payload = _make_issue_payload(
            comment_body="/assign",
            comment_user={"login": "bot", "type": "Bot"},
        )
        assigns, unassigns = [], []
        self._run_comment(payload, assigns, unassigns)
        self.assertEqual(assigns, [])
        self.assertEqual(unassigns, [])

    def test_ignores_unrelated_comments(self):
        payload = _make_issue_payload(comment_body="just a comment")
        assigns, unassigns = [], []
        self._run_comment(payload, assigns, unassigns)
        self.assertEqual(assigns, [])
        self.assertEqual(unassigns, [])


class TestHandleIssueOpened(unittest.TestCase):
    """handle_issue_opened — mirrors handleIssueOpened in issue-opened.test.js"""

    def _run_opened(self, payload, comments, bug_calls, bug_return=None):
        async def _inner():
            async def _mock_report(url, data):
                bug_calls.append(data)
                return bug_return

            with (
                patch.object(_worker, "create_comment", new=AsyncMock(side_effect=lambda o, r, n, b, t: comments.append(b))),
                patch.object(_worker, "report_bug_to_blt", new=_mock_report),
            ):
                await _worker.handle_issue_opened(payload, "tok", "https://blt.example")
        _run(_inner())

    def test_posts_welcome_message(self):
        payload = _make_issue_payload()
        comments, bugs = [], []
        self._run_opened(payload, comments, bugs)
        self.assertEqual(len(comments), 1)
        self.assertIn("Thanks for opening this issue", comments[0])
        self.assertIn("/assign", comments[0])

    def test_reports_bug_to_blt_for_bug_label(self):
        payload = _make_issue_payload(labels=[{"name": "bug"}])
        comments, bugs = [], []
        self._run_opened(payload, comments, bugs, bug_return={"id": 42})
        self.assertEqual(len(bugs), 1)
        self.assertIn("Bug ID: #42", comments[0])

    def test_does_not_report_bug_without_bug_label(self):
        payload = _make_issue_payload(labels=[])
        comments, bugs = [], []
        self._run_opened(payload, comments, bugs)
        self.assertEqual(bugs, [])

    def test_ignores_bot_senders(self):
        payload = _make_issue_payload(sender={"login": "bot", "type": "Bot"})
        comments, bugs = [], []
        self._run_opened(payload, comments, bugs)
        self.assertEqual(comments, [])


class TestHandleIssueLabeled(unittest.TestCase):
    """handle_issue_labeled — mirrors handleIssueLabeled in issue-opened.test.js"""

    def _run_labeled(self, payload, comments, bug_calls, bug_return=None):
        async def _inner():
            async def _mock_report(url, data):
                bug_calls.append(data)
                return bug_return

            with (
                patch.object(_worker, "create_comment", new=AsyncMock(side_effect=lambda o, r, n, b, t: comments.append(b))),
                patch.object(_worker, "report_bug_to_blt", new=_mock_report),
            ):
                await _worker.handle_issue_labeled(payload, "tok", "https://blt.example")
        _run(_inner())

    def test_reports_to_blt_when_bug_label_added(self):
        payload = _make_issue_payload(
            labels=[{"name": "bug"}],
            label={"name": "bug"},
        )
        comments, bugs = [], []
        self._run_labeled(payload, comments, bugs, bug_return={"id": 42})
        self.assertEqual(len(bugs), 1)
        self.assertIn("Bug ID: #42", comments[0])

    def test_does_not_report_for_non_bug_labels(self):
        payload = _make_issue_payload(
            labels=[{"name": "enhancement"}],
            label={"name": "enhancement"},
        )
        comments, bugs = [], []
        self._run_labeled(payload, comments, bugs)
        self.assertEqual(bugs, [])

    def test_does_not_report_if_bug_label_already_present(self):
        payload = _make_issue_payload(
            labels=[{"name": "bug"}, {"name": "vulnerability"}],
            label={"name": "vulnerability"},
        )
        comments, bugs = [], []
        self._run_labeled(payload, comments, bugs)
        self.assertEqual(bugs, [])


class TestHandlePullRequestOpened(unittest.TestCase):
    """handle_pull_request_opened — mirrors handlePullRequestOpened in pull-request.test.js"""

    def _run_opened(self, payload, comments):
        async def _inner():
            with patch.object(_worker, "create_comment", new=AsyncMock(side_effect=lambda o, r, n, b, t: comments.append(b))):
                await _worker.handle_pull_request_opened(payload, "tok")
        _run(_inner())

    def test_posts_welcome_message(self):
        payload = _make_pr_payload()
        comments = []
        self._run_opened(payload, comments)
        self.assertEqual(len(comments), 1)
        self.assertIn("Thanks for opening this pull request", comments[0])
        self.assertIn("OWASP BLT", comments[0])

    def test_ignores_bot_senders(self):
        payload = _make_pr_payload(sender={"login": "bot", "type": "Bot"})
        comments = []
        self._run_opened(payload, comments)
        self.assertEqual(comments, [])


class TestHandlePullRequestClosed(unittest.TestCase):
    """handle_pull_request_closed — mirrors handlePullRequestClosed in pull-request.test.js"""

    def _run_closed(self, payload, comments):
        async def _inner():
            with patch.object(_worker, "create_comment", new=AsyncMock(side_effect=lambda o, r, n, b, t: comments.append(b))):
                await _worker.handle_pull_request_closed(payload, "tok")
        _run(_inner())

    def test_posts_congratulations_when_merged(self):
        payload = _make_pr_payload(merged=True)
        comments = []
        self._run_closed(payload, comments)
        self.assertEqual(len(comments), 1)
        self.assertIn("PR merged", comments[0])
        self.assertIn("alice", comments[0])

    def test_does_not_post_when_not_merged(self):
        payload = _make_pr_payload(merged=False)
        comments = []
        self._run_closed(payload, comments)
        self.assertEqual(comments, [])

    def test_ignores_bot_merges(self):
        payload = _make_pr_payload(merged=True, sender={"login": "bot", "type": "Bot"})
        comments = []
        self._run_closed(payload, comments)
        self.assertEqual(comments, [])


class TestSecretVarsStatusHtml(unittest.TestCase):
    """_secret_vars_status_html and _landing_html secret variable display"""

    def _make_env(self, **attrs):
        env = types.SimpleNamespace()
        for k, v in attrs.items():
            setattr(env, k, v)
        return env

    def test_required_vars_set_shows_green(self):
        env = self._make_env(APP_ID="123", PRIVATE_KEY="pem", WEBHOOK_SECRET="secret")
        html = _worker._secret_vars_status_html(env)
        self.assertIn("APP_ID", html)
        self.assertIn("PRIVATE_KEY", html)
        self.assertIn("WEBHOOK_SECRET", html)
        # All three required vars are set — should show "Set" badge (green #4ade80)
        self.assertEqual(html.count("4ade80"), 3)

    def test_required_vars_missing_shows_red(self):
        env = self._make_env()  # no attributes set
        html = _worker._secret_vars_status_html(env)
        # All three required vars missing — should show "Not set" badge (red #f87171)
        self.assertEqual(html.count("f87171"), 3)

    def test_optional_vars_set_shows_green(self):
        env = self._make_env(GITHUB_CLIENT_ID="cid", GITHUB_CLIENT_SECRET="csec")
        html = _worker._secret_vars_status_html(env)
        self.assertIn("GITHUB_CLIENT_ID", html)
        self.assertIn("GITHUB_CLIENT_SECRET", html)
        self.assertEqual(html.count("4ade80"), 2)

    def test_optional_vars_missing_shows_gray(self):
        env = self._make_env()
        html = _worker._secret_vars_status_html(env)
        # Optional vars missing — should show "Not configured" badge (gray #9ca3af)
        self.assertEqual(html.count("9ca3af"), 2)

    def test_optional_label_present(self):
        env = self._make_env()
        html = _worker._secret_vars_status_html(env)
        self.assertIn("(optional)", html)

    def test_landing_html_includes_secret_vars(self):
        env = self._make_env(APP_ID="123", PRIVATE_KEY="pem", WEBHOOK_SECRET="sec")
        html = _worker._landing_html("my-app", env)
        self.assertIn("APP_ID", html)
        self.assertIn("PRIVATE_KEY", html)
        self.assertIn("WEBHOOK_SECRET", html)
        self.assertIn("GITHUB_CLIENT_ID", html)
        self.assertIn("GITHUB_CLIENT_SECRET", html)
        # Placeholder should be replaced
        self.assertNotIn("{{SECRET_VARS_STATUS}}", html)

    def test_landing_html_no_env_removes_placeholder(self):
        html = _worker._landing_html("my-app", None)
        self.assertNotIn("{{SECRET_VARS_STATUS}}", html)


class TestCreateGithubJwt(unittest.TestCase):
    """create_github_jwt — verifies to_js is used for SubtleCrypto parameters."""

    class _Uint8ArrayStub:
        """Minimal Uint8Array stand-in for use outside the Cloudflare runtime."""

        def __init__(self, n_or_buf=0):
            self._data = bytearray(n_or_buf)
            self.buffer = self._data

        @classmethod
        def new(cls, n_or_buf=0):
            return cls(n_or_buf)

        def __setitem__(self, i, v):
            self._data[i] = v

        def __iter__(self):
            return iter(self._data)

        def __bytes__(self):
            return bytes(self._data)

    def _make_rsa_pem(self) -> str:
        """Return a minimal (non-functional) PKCS#8 PEM for import testing."""
        # 16 zero bytes wrapped in a PKCS#8 PEM header
        payload = base64.b64encode(bytes(16)).decode()
        return f"-----BEGIN PRIVATE KEY-----\n{payload}\n-----END PRIVATE KEY-----"

    def _run_create_jwt(self, spy_to_js):
        """Run create_github_jwt with mocked JS and pyodide.ffi modules."""
        mock_import_key = AsyncMock(return_value=object())
        mock_sign = AsyncMock(return_value=bytes(64))
        mock_subtle = types.SimpleNamespace(importKey=mock_import_key, sign=mock_sign)

        async def _inner():
            with patch.dict(
                sys.modules,
                {
                    "js": types.SimpleNamespace(
                        Uint8Array=self._Uint8ArrayStub,
                        crypto=types.SimpleNamespace(subtle=mock_subtle),
                    ),
                    "pyodide.ffi": types.SimpleNamespace(to_js=spy_to_js),
                },
            ):
                return await _worker.create_github_jwt("123", self._make_rsa_pem())

        asyncio.run(_inner())

    def test_to_js_called_for_key_usages(self):
        """to_js must be called with the keyUsages list so SubtleCrypto receives a JS Array."""
        to_js_calls = []

        def _spy(value, **kw):
            to_js_calls.append(value)
            return value

        self._run_create_jwt(_spy)
        self.assertIn(["sign"], to_js_calls)

    def test_to_js_called_for_algorithm(self):
        """to_js must be called with the algorithm dict so SubtleCrypto receives a JS Object."""
        to_js_calls = []

        def _spy(value, **kw):
            to_js_calls.append(value)
            return value

        self._run_create_jwt(_spy)
        self.assertTrue(
            any(isinstance(v, dict) and v.get("name") == "RSASSA-PKCS1-v1_5" for v in to_js_calls)
        )


if __name__ == "__main__":
    unittest.main()
