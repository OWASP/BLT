"""
defaults.py

Default configuration values for the BLT Preflight advisory pipeline.

These values act as the application's built-in configuration and may
be overridden by user-defined configuration (e.g. preflight.yaml)
in later development stages.

This module should contain ONLY configuration constants.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Retrieval Configuration
# ---------------------------------------------------------------------------

#: Minimum similarity score required for a retrieved document
#: to be considered relevant.
SIMILARITY_THRESHOLD: float = 0.60

#: Number of highest-ranked documents forwarded to the LLM.
TOP_K: int = 3

#: Maximum number of retrieval results to inspect before filtering.
MAX_RETRIEVAL_RESULTS: int = 10

# ---------------------------------------------------------------------------
# Context Configuration
# ---------------------------------------------------------------------------

#: Maximum number of characters allowed per retrieved chunk.
MAX_CHUNK_LENGTH: int = 2000

#: Maximum combined context length passed to the LLM.
MAX_CONTEXT_CHARACTERS: int = 8000

# ---------------------------------------------------------------------------
# LLM Configuration
# ---------------------------------------------------------------------------

#: Default LLM request timeout (seconds).
LLM_TIMEOUT_SECONDS: int = 10

#: Maximum retry attempts for failed LLM requests.
MAX_RETRIES: int = 2

#: Temperature used for deterministic advisory generation.
DEFAULT_TEMPERATURE: float = 0.0

# ---------------------------------------------------------------------------
# Cache Configuration
# ---------------------------------------------------------------------------

#: Maximum number of cached retrieval entries.
RETRIEVAL_CACHE_SIZE: int = 512

#: Maximum number of cached embedding entries.
EMBEDDING_CACHE_SIZE: int = 1024

#: Cache time-to-live (seconds).
CACHE_TTL_SECONDS: int = 3600

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------

#: Default logging level.
LOG_LEVEL: str = "INFO"

#: Enable performance metrics collection.
ENABLE_METRICS: bool = True

#: Enable cache statistics.
ENABLE_CACHE_STATS: bool = True

# ---------------------------------------------------------------------------
# Advisory Configuration
# ---------------------------------------------------------------------------

#: Default severity used when generation falls back.
DEFAULT_SEVERITY: str = "MEDIUM"

#: Whether deterministic fallback advisories are enabled.
ENABLE_FALLBACK: bool = True

#: Require at least one retrieved document before LLM generation.
REQUIRE_RETRIEVAL_CONTEXT: bool = True

# ---------------------------------------------------------------------------
# Validation Configuration
# ---------------------------------------------------------------------------

#: Remove duplicate retrieved chunks.
REMOVE_DUPLICATES: bool = True

#: Validate retrieval metadata before generation.
VALIDATE_METADATA: bool = True

#: Validate advisory schema before returning output.
VALIDATE_SCHEMA: bool = True

# ---------------------------------------------------------------------------
# Pipeline Configuration
# ---------------------------------------------------------------------------

#: Continue pipeline execution when optional stages fail.
CONTINUE_ON_NON_CRITICAL_FAILURE: bool = True

#: Enable execution timing.
ENABLE_PIPELINE_TIMING: bool = True