"""
Unit tests for the logging subsystem.
"""

from __future__ import annotations

import json
import logging

from advisory_engine.logging.logger import (
    configure_logging,
    get_logger,
    PipelineLogger,
)

from advisory_engine.logging.formatter import (
    StructuredFormatter,
    JsonFormatter,
    build_extra,
)


# ---------------------------------------------------------------------
# Logger Configuration
# ---------------------------------------------------------------------


def test_get_logger():
    """
    Verify logger creation.
    """

    logger = get_logger("test")

    assert logger.name == "test"


def test_pipeline_logger():
    """
    Verify PipelineLogger wrapper.
    """

    logger = PipelineLogger("pipeline")

    logger.info("info")

    logger.debug("debug")

    logger.warning("warning")

    logger.error("error")

    assert logger.logger.name == "pipeline"


def test_configure_logging():
    """
    Configure logging without errors.
    """

    configure_logging(level="DEBUG")

    logger = logging.getLogger()

    assert logger.level == logging.DEBUG


# ---------------------------------------------------------------------
# File Logging
# ---------------------------------------------------------------------


def test_log_file_creation(tmp_path):
    """
    Verify log file is created.
    """

    log_file = tmp_path / "preflight.log"

    configure_logging(
        level="INFO",
        log_file=str(log_file),
    )

    logger = get_logger("test")

    logger.info("Hello World")

    for handler in logging.getLogger().handlers:
        handler.flush()

    assert log_file.exists()

    content = log_file.read_text(
        encoding="utf-8",
    )

    assert "Hello World" in content


# ---------------------------------------------------------------------
# Structured Formatter
# ---------------------------------------------------------------------


def test_structured_formatter():
    """
    Verify human-readable formatting.
    """

    formatter = StructuredFormatter()

    record = logging.LogRecord(
        name="pipeline",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Retriever completed",
        args=(),
        exc_info=None,
    )

    record.stage = "retrieval"

    record.duration_ms = 42.5

    output = formatter.format(record)

    assert "Retriever completed" in output

    assert "retrieval" in output

    assert "42.50ms" in output


def test_structured_formatter_confidence():
    """
    Verify confidence field.
    """

    formatter = StructuredFormatter()

    record = logging.LogRecord(
        "pipeline",
        logging.INFO,
        __file__,
        1,
        "Evaluation",
        (),
        None,
    )

    record.confidence = "High"

    output = formatter.format(record)

    assert "High" in output


# ---------------------------------------------------------------------
# JSON Formatter
# ---------------------------------------------------------------------


def test_json_formatter():
    """
    Verify JSON formatting.
    """

    formatter = JsonFormatter()

    record = logging.LogRecord(
        "pipeline",
        logging.INFO,
        __file__,
        1,
        "Pipeline finished",
        (),
        None,
    )

    record.stage = "evaluation"

    output = formatter.format(record)

    payload = json.loads(output)

    assert payload["message"] == "Pipeline finished"

    assert payload["stage"] == "evaluation"

    assert payload["level"] == "INFO"


def test_json_formatter_extra_fields():
    """
    Verify optional metadata fields.
    """

    formatter = JsonFormatter()

    record = logging.LogRecord(
        "pipeline",
        logging.INFO,
        __file__,
        1,
        "Completed",
        (),
        None,
    )

    record.request_id = "abc123"

    record.pipeline = "preflight"

    record.duration_ms = 18.4

    output = formatter.format(record)

    payload = json.loads(output)

    assert payload["request_id"] == "abc123"

    assert payload["pipeline"] == "preflight"

    assert payload["duration_ms"] == 18.4


# ---------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------


def test_build_extra():
    """
    Verify helper dictionary.
    """

    extra = build_extra(
        stage="retrieval",
        duration_ms=30,
        confidence="High",
    )

    assert extra["stage"] == "retrieval"

    assert extra["duration_ms"] == 30

    assert extra["confidence"] == "High"


# ---------------------------------------------------------------------
# Exception Formatting
# ---------------------------------------------------------------------


def test_json_formatter_exception():
    """
    Verify exception serialization.
    """

    formatter = JsonFormatter()

    try:

        raise RuntimeError("Boom")

    except RuntimeError:

        record = logging.LogRecord(
            "pipeline",
            logging.ERROR,
            __file__,
            1,
            "Failure",
            (),
            None,
        )

        record.exc_info = True.__class__, RuntimeError(
            "Boom"
        ), None

        output = formatter.format(record)

        payload = json.loads(output)

        assert payload["level"] == "ERROR"

        assert "exception" in payload