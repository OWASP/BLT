"""Build ``fetch()`` init objects that the Workers runtime can read.

A Python ``dict`` handed straight to JS ``fetch`` arrives as a PyProxy, and
JS reads ``init.method`` / ``init.body`` / ``init.headers`` as properties, which
a dict proxy does not expose. The request then goes out as a bare GET with no
body or headers: GitHub's token exchange, BLT-API posts and webhooks all fail
that way. Converting with ``Object.fromEntries`` gives fetch a real object.
"""

from __future__ import annotations

from typing import Any, Mapping


def fetch_init(init: Mapping[str, Any]) -> Any:
    """Return ``init`` as a JS object on Workers, or unchanged elsewhere."""
    try:
        from js import Object  # type: ignore[import-not-found]
        from pyodide.ffi import to_js  # type: ignore[import-not-found]
    except ImportError:
        return dict(init)
    return to_js(dict(init), dict_converter=Object.fromEntries)
