import urllib.parse
from unittest.mock import AsyncMock, MagicMock


def parse_path(url):
    """
    Extract clean path from URL, handling query params and fragments.
    This is a copy of the function from worker.py for testing purposes.

    ⚠️  KEEP IN SYNC WITH worker.py parse_path() ⚠️

    Args:
        url: The full URL string

    Returns:
        str: The path component of the URL
    """
    parsed = urllib.parse.urlparse(url)
    path = parsed.path
    if not path or path == "":
        path = "/"
    elif not path.startswith("/"):
        path = "/" + path
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path


def make_d1_mock(first_return=None, run_meta=None):
    """Build a mock Cloudflare D1 database handle using the prepare().bind() API.

    Returns a MagicMock whose ``prepare(sql).bind(*args)`` chain exposes:
    - ``.first()`` — async, returns ``first_return``
    - ``.all()`` — async, returns a MagicMock with ``results=[]``
    - ``.run()`` — async, returns a result with ``meta.changes``

    Usage::

        db = make_d1_mock(first_return={"status": "redaction_passed"})
        db = make_d1_mock(first_return=None)  # simulate row not found
    """
    if run_meta is None:
        run_meta = {"changes": 1}

    mock_run_result = MagicMock()
    mock_run_result.meta = MagicMock()
    mock_run_result.meta.changes = run_meta.get("changes", 1)

    stmt = MagicMock()
    stmt.bind = MagicMock(return_value=stmt)
    stmt.first = AsyncMock(return_value=first_return)
    stmt.run = AsyncMock(return_value=mock_run_result)
    stmt.all = AsyncMock(return_value=MagicMock(results=[]))

    db = MagicMock()
    db.prepare = MagicMock(return_value=stmt)
    return db
