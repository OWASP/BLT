"""
formatter.py

Custom log formatters for BLT Preflight.

Responsibilities
----------------
- Human-readable console formatting
- Structured JSON logging
- Optional contextual metadata
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any


class StructuredFormatter(logging.Formatter):
    """
    Human-readable structured formatter.
    """

    default_time_format = "%Y-%m-%d %H:%M:%S"

    def format(
        self,
        record: logging.LogRecord,
    ) -> str:

        timestamp = datetime.fromtimestamp(
            record.created
        ).strftime(self.default_time_format)

        parts = [
            timestamp,
            record.levelname,
            record.name,
            record.getMessage(),
        ]

        if hasattr(record, "stage"):
            parts.append(
                f"stage={record.stage}"
            )

        if hasattr(record, "confidence"):
            parts.append(
                f"confidence={record.confidence}"
            )

        if hasattr(record, "duration_ms"):
            parts.append(
                f"duration={record.duration_ms:.2f}ms"
            )

        return " | ".join(parts)


class JsonFormatter(logging.Formatter):
    """
    JSON log formatter.
    """

    def format(
        self,
        record: logging.LogRecord,
    ) -> str:

        payload: dict[str, Any] = {
            "timestamp": datetime.utcfromtimestamp(
                record.created
            ).isoformat()
            + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        optional = [
            "stage",
            "confidence",
            "duration_ms",
            "request_id",
            "pipeline",
            "repository",
        ]

        for field in optional:
            if hasattr(record, field):
                payload[field] = getattr(
                    record,
                    field,
                )

        if record.exc_info:
            payload["exception"] = self.formatException(
                record.exc_info
            )

        return json.dumps(
            payload,
            ensure_ascii=False,
        )


def build_extra(
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Helper for logging extra context.

    Example:
        logger.info(
            "Retriever finished",
            extra=build_extra(
                stage="retrieval",
                duration_ms=45.3,
            ),
        )
    """

    return kwargs