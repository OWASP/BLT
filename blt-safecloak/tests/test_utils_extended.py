"""
Extended unit tests for src/libs/utils.py.

Covers functions and edge-cases not exercised by test_utils.py:
  - normalize_origin (edge cases)
  - add_vary_origin  (merging into existing Vary headers)
  - get_allowed_origins (empty / multi-origin env var)
  - base_headers  (all three combinations: no origin, allowed, blocked)
  - html_response / json_response / cors_response with custom status codes
  - resolve_allowed_origin with None input
  - multiple comma-separated allowed origins
"""

import sys
import os
import json

import pytest

# ── Cloudflare workers mock ──────────────────────────────────────────────────
if 'workers' not in sys.modules:
    from unittest.mock import MagicMock

    _mock_workers = MagicMock()

    class _FakeResponse:
        def __init__(self, body, status=200, headers=None):
            raw = body or ''
            self.body = raw.encode('utf-8') if isinstance(raw, str) else raw
            self.status_code = status
            self.headers = headers or {}

    _mock_workers.Response = _FakeResponse
    _mock_workers.WorkerEntrypoint = type('WorkerEntrypoint', (), {})
    sys.modules['workers'] = _mock_workers

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.libs.utils import (  # noqa: E402
    normalize_origin,
    add_vary_origin,
    get_allowed_origins,
    base_headers,
    html_response,
    json_response,
    cors_response,
    resolve_allowed_origin,
)


# ── normalize_origin ─────────────────────────────────────────────────────────


def test_normalize_origin_lowercases_scheme_and_host():
    assert normalize_origin('HTTPS://EXAMPLE.COM') == 'https://example.com'


def test_normalize_origin_strips_trailing_slash():
    assert normalize_origin('https://example.com/') == 'https://example.com'


def test_normalize_origin_strips_trailing_slash_and_lowercases():
    assert normalize_origin('HTTPS://Example.COM/') == 'https://example.com'


def test_normalize_origin_no_scheme_returns_lowercased_value():
    """Strings without a scheme/netloc should be lower-cased as-is."""
    result = normalize_origin('SomeRawValue')
    assert result == 'somerawvalue'


def test_normalize_origin_with_port_preserved():
    assert normalize_origin('https://example.com:8443') == 'https://example.com:8443'


def test_normalize_origin_strips_internal_whitespace():
    """Leading/trailing whitespace is stripped by the normalize call."""
    assert normalize_origin('  https://example.com  ') == 'https://example.com'


# ── add_vary_origin ───────────────────────────────────────────────────────────


def test_add_vary_origin_adds_header_when_absent():
    headers: dict = {}
    add_vary_origin(headers)
    assert headers['Vary'] == 'Origin'


def test_add_vary_origin_does_not_duplicate_when_already_present():
    headers = {'Vary': 'Origin'}
    add_vary_origin(headers)
    # Exactly one Origin in the final Vary value
    parts = [p.strip() for p in headers['Vary'].split(',')]
    assert parts.count('Origin') == 1


def test_add_vary_origin_appends_to_existing_vary_values():
    headers = {'Vary': 'Accept-Encoding, Accept-Language'}
    add_vary_origin(headers)
    parts = [p.strip() for p in headers['Vary'].split(',')]
    assert 'Origin' in parts
    assert 'Accept-Encoding' in parts
    assert 'Accept-Language' in parts


def test_add_vary_origin_does_not_add_duplicate_to_multi_value():
    headers = {'Vary': 'Accept-Encoding, Origin'}
    add_vary_origin(headers)
    parts = [p.strip() for p in headers['Vary'].split(',')]
    assert parts.count('Origin') == 1


# ── get_allowed_origins ───────────────────────────────────────────────────────


def test_get_allowed_origins_empty_env_returns_empty_set(monkeypatch):
    monkeypatch.setenv('SAFE_CLOAK_ALLOWED_ORIGINS', '')
    result = get_allowed_origins()
    assert isinstance(result, set)
    assert len(result) == 0


def test_get_allowed_origins_single_origin(monkeypatch):
    monkeypatch.setenv('SAFE_CLOAK_ALLOWED_ORIGINS', 'https://single.example')
    result = get_allowed_origins()
    assert result == {'https://single.example'}


def test_get_allowed_origins_multiple_origins(monkeypatch):
    monkeypatch.setenv('SAFE_CLOAK_ALLOWED_ORIGINS',
                       'https://first.example,https://second.example')
    result = get_allowed_origins()
    assert result == {'https://first.example', 'https://second.example'}


def test_get_allowed_origins_normalises_case_in_list(monkeypatch):
    monkeypatch.setenv('SAFE_CLOAK_ALLOWED_ORIGINS', 'HTTPS://UPPER.EXAMPLE')
    result = get_allowed_origins()
    assert result == {'https://upper.example'}


def test_get_allowed_origins_ignores_blank_entries(monkeypatch):
    monkeypatch.setenv('SAFE_CLOAK_ALLOWED_ORIGINS', 'https://a.example,,https://b.example')
    result = get_allowed_origins()
    # Exact set equality: two origins only, no blank entry
    assert result == {'https://a.example', 'https://b.example'}


# ── resolve_allowed_origin ────────────────────────────────────────────────────


def test_resolve_allowed_origin_none_returns_none():
    assert resolve_allowed_origin(None) is None


def test_resolve_allowed_origin_empty_string_returns_none():
    assert resolve_allowed_origin('') is None


def test_resolve_allowed_origin_returns_normalised_form(monkeypatch):
    monkeypatch.setenv('SAFE_CLOAK_ALLOWED_ORIGINS', 'https://Example.COM')
    result = resolve_allowed_origin('https://EXAMPLE.com')
    assert result == 'https://example.com'


def test_resolve_allowed_origin_unknown_returns_none(monkeypatch):
    monkeypatch.setenv('SAFE_CLOAK_ALLOWED_ORIGINS', 'https://allowed.example')
    assert resolve_allowed_origin('https://notallowed.example') is None


# ── base_headers ──────────────────────────────────────────────────────────────


def test_base_headers_no_origin_no_vary_no_acao():
    """When origin is None, Vary and ACAO headers should be absent."""
    h = base_headers('text/plain', origin=None)
    assert h['Content-Type'] == 'text/plain'
    assert 'Vary' not in h
    assert 'Access-Control-Allow-Origin' not in h


def test_base_headers_with_allowed_origin_sets_acao(monkeypatch):
    monkeypatch.setenv('SAFE_CLOAK_ALLOWED_ORIGINS', 'https://trusted.example')
    h = base_headers('text/html; charset=utf-8', origin='https://trusted.example')
    assert h['Access-Control-Allow-Origin'] == 'https://trusted.example'
    assert h['Vary'] == 'Origin'


def test_base_headers_with_unknown_origin_sets_vary_but_no_acao(monkeypatch):
    monkeypatch.setenv('SAFE_CLOAK_ALLOWED_ORIGINS', 'https://trusted.example')
    h = base_headers('application/json', origin='https://untrusted.example')
    assert 'Access-Control-Allow-Origin' not in h
    assert h['Vary'] == 'Origin'


# ── html_response ─────────────────────────────────────────────────────────────


def test_html_response_custom_201_status():
    resp = html_response('<html/>', status=201)
    assert resp.status_code == 201


def test_html_response_body_is_html():
    resp = html_response('<h1>Hello</h1>')
    assert b'<h1>Hello</h1>' in resp.body


def test_html_response_content_type_is_html():
    resp = html_response('<!doctype html>')
    assert resp.headers['Content-Type'] == 'text/html; charset=utf-8'


# ── json_response ─────────────────────────────────────────────────────────────


def test_json_response_non_200_status():
    resp = json_response({'error': 'bad request'}, status=400)
    assert resp.status_code == 400
    assert json.loads(resp.body) == {'error': 'bad request'}


def test_json_response_unicode_preserved():
    resp = json_response({'greeting': 'こんにちは'})
    data = json.loads(resp.body.decode('utf-8'))
    assert data['greeting'] == 'こんにちは'


def test_json_response_content_type_is_json():
    resp = json_response({})
    assert resp.headers['Content-Type'] == 'application/json; charset=utf-8'


# ── cors_response ─────────────────────────────────────────────────────────────


def test_cors_response_none_origin_no_acao():
    resp = cors_response(origin=None)
    assert resp.status_code == 204
    assert 'Access-Control-Allow-Origin' not in resp.headers


def test_cors_response_custom_status():
    resp = cors_response(status=200)
    assert resp.status_code == 200


def test_cors_response_always_has_max_age():
    resp = cors_response()
    assert resp.headers.get('Access-Control-Max-Age') == '86400'


def test_cors_response_always_has_vary():
    resp = cors_response()
    assert resp.headers.get('Vary') == 'Origin'
