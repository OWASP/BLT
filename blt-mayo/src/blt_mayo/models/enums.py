from __future__ import annotations

from enum import StrEnum


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ArtifactType(StrEnum):
    SHELL_SCRIPT = "shell_script"
    PYTHON_SCRIPT = "python_script"
    CONFIG = "config"
    CRON = "cron"
    SYSTEMD_UNIT = "systemd_unit"
    STARTUP_HOOK = "startup_hook"
    SSH_CONFIG = "ssh_config"
    HIDDEN_EXECUTABLE = "hidden_executable"
    BINARY = "binary"
    UNKNOWN = "unknown"


class PathSensitivity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewStatus(StrEnum):
    OPEN = "open"
    REVIEWED = "reviewed"
    IGNORED = "ignored"
    ACCEPTED_RISK = "accepted-risk"
    ESCALATED = "escalated"
    EXPORT_READY = "export-ready"
    SUBMITTED_TO_BLT = "submitted-to-blt"
