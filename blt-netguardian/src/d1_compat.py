"""Normalize Cloudflare D1 result objects for local SqliteDB and production.

On the Workers runtime, D1 returns JavaScript proxy objects (``JsProxy``).
Reading columns off them with ``row["id"]`` yields ``None``; they must be
converted to native Python structures with Pyodide's ``.to_py()`` first.
Locally, the SqliteDB shim already returns plain ``dict`` rows, so these
helpers are no-ops there.
"""

from __future__ import annotations

from typing import Any, Optional


def _to_py(value: Any) -> Any:
    """Convert a Pyodide JsProxy into native Python, leaving dicts/lists alone."""
    if value is None or isinstance(value, (dict, list, str, int, float, bool)):
        return value
    to_py = getattr(value, "to_py", None)
    if callable(to_py):
        try:
            converted = to_py()
        except Exception:  # noqa: BLE001 - defensive against runtime quirks
            return value
        if isinstance(converted, dict):
            return converted
        # to_py may produce a Map -> list of pairs; coerce when possible.
        try:
            return dict(converted)
        except (TypeError, ValueError):
            return converted
    return value


def _coerce_row(row: Any) -> Optional[dict]:
    if row is None:
        return None
    converted = _to_py(row)
    if isinstance(converted, dict):
        return converted
    # Fallback: mapping-like object exposing keys().
    keys = getattr(converted, "keys", None)
    if callable(keys):
        try:
            return {str(k): converted[k] for k in keys()}
        except (KeyError, TypeError, ValueError):
            return None
    return None


def row_get(row: Any, key: str, default: Any = None) -> Any:
    """Read a column from a D1 row (dict or Workers JsProxy)."""
    coerced = _coerce_row(row)
    if coerced is None:
        return default
    return coerced.get(key, default)


def d1_rows(result: Any) -> list:
    """Extract normalized row dicts from D1 .all() / .run() or the local shim."""
    if result is None:
        return []
    rows = getattr(result, "results", None)
    if rows is None and isinstance(result, dict):
        rows = result.get("results")
    if rows is None:
        return []
    rows = _to_py(rows)
    normalized: list[dict] = []
    for row in rows:
        coerced = _coerce_row(row)
        if coerced is not None:
            normalized.append(coerced)
    return normalized


def d1_row(result: Any) -> Optional[dict]:
    """Extract a single normalized row dict from D1 .first() or None."""
    return _coerce_row(result)
