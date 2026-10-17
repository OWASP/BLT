"""Credential guardrails for the detection export CLI."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "detect_export.py"


def _load_detect_export():
    # scripts/ is not a package; load by path so tests stay isolated from cwd.
    spec = importlib.util.spec_from_file_location("detect_export", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


detect_export = _load_detect_export()


def test_loopback_gets_demo_secret_and_payload_key_when_encrypting():
    secret, key = detect_export._resolve_credentials(
        "http://localhost:8787", secret_hex=None, payload_key=None, encrypt=True
    )
    assert secret == detect_export.DEMO_SECRET_HEX
    assert key == detect_export.DEMO_PAYLOAD_KEY


def test_loopback_plaintext_does_not_require_payload_key():
    secret, key = detect_export._resolve_credentials(
        "http://127.0.0.1:8787", secret_hex=None, payload_key=None, encrypt=False
    )
    assert secret == detect_export.DEMO_SECRET_HEX
    assert key is None


def test_remote_plaintext_requires_secret_only():
    secret, key = detect_export._resolve_credentials(
        "https://staging.example.workers.dev",
        secret_hex="aabb",
        payload_key=None,
        encrypt=False,
    )
    assert secret == "aabb"
    assert key is None


def test_remote_encrypted_requires_payload_key():
    with pytest.raises(SystemExit, match="payload-key-b64"):
        detect_export._resolve_credentials(
            "https://staging.example.workers.dev",
            secret_hex="aabb",
            payload_key=None,
            encrypt=True,
        )


def test_remote_always_requires_secret():
    with pytest.raises(SystemExit, match="secret-hex"):
        detect_export._resolve_credentials(
            "https://staging.example.workers.dev",
            secret_hex=None,
            payload_key=None,
            encrypt=False,
        )


def test_remote_never_falls_back_to_demo_credentials():
    with pytest.raises(SystemExit):
        detect_export._resolve_credentials(
            "https://example.com", secret_hex=None, payload_key=None, encrypt=True
        )
