"""Structured advisory schema (compatibility shim).

The models live in ``advisory_engine.rag.schema``; this module re-exports them
for code that imports ``schema`` from the repository root.
"""

from __future__ import annotations

import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from advisory_engine.rag.schema import (  # noqa: E402
    Advisory,
    AdvisorySchema,
    Reference,
    Severity,
    StructuredAdvisory,
)

__all__ = ["Advisory", "AdvisorySchema", "Reference", "Severity", "StructuredAdvisory"]
