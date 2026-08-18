"""Detect proxy API."""

from __future__ import annotations

import pytest

from detect_service import detect_headers_for_request


@pytest.mark.asyncio
async def test_detect_headers_example_com():
    status, body = await detect_headers_for_request({"url": "https://example.com"})
    assert status == 200
    assert body["count"] >= 1
    rule_ids = {f["rule_id"] for f in body["findings"]}
    assert "http.missing-hsts" in rule_ids
