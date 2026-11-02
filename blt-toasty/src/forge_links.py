"""Links to BLT forge pages, shared so every module builds them the same way."""

from __future__ import annotations

from typing import Any

ISSUE_URL_TEMPLATE = "https://git.owaspblt.org/BLT/issues/{iid}"


def issue_url(issue_iid: Any) -> str:
    """Return the forge URL for issue number *issue_iid*."""
    return ISSUE_URL_TEMPLATE.format(iid=issue_iid)
