"""Storage layer — D1 native query helpers.

Typed query helpers for every table. No Database wrapper, no aiosqlite.
Pass the D1 binding directly to each query class.
"""

from .d1_utils import d1_row, d1_rows, dumps_json, loads_json, parse_utc, utc_now_iso
from .queries import (
    AvatarStateQueries,
    ContributorQueries,
    CursorQueries,
    DeadLetterQueries,
    EventQueries,
    IdentityQueries,
)

__all__ = [
    "EventQueries",
    "ContributorQueries",
    "AvatarStateQueries",
    "IdentityQueries",
    "CursorQueries",
    "DeadLetterQueries",
    "utc_now_iso",
    "parse_utc",
    "dumps_json",
    "loads_json",
]
