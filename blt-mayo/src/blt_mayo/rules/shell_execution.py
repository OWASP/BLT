from __future__ import annotations

import re
from dataclasses import dataclass

from blt_mayo.models.enums import Confidence, Severity


@dataclass(frozen=True, slots=True)
class ShellExecutionRule:
    """A single explainable shell dangerous-execution rule."""

    rule_id: str
    title: str
    pattern: re.Pattern[str]
    severity: Severity
    confidence: Confidence
    description: str
    remediation: str
    tags: tuple[str, ...]


SHELL_EXECUTION_RULES: tuple[ShellExecutionRule, ...] = (
    ShellExecutionRule(
        rule_id="SHELL-PIPE-TO-SHELL",
        title="Remote content piped directly to a shell",
        pattern=re.compile(
            r"\b(?:curl|wget)\b[^|\n]*\|\s*(?:sudo\s+)?(?:bash|sh|zsh|ksh)\b",
            re.IGNORECASE,
        ),
        severity=Severity.CRITICAL,
        confidence=Confidence.HIGH,
        description=(
            "A remote response is passed directly to a command shell without a separate "
            "integrity or authenticity verification step."
        ),
        remediation=(
            "Download the file to a controlled location, verify its source and checksum, "
            "review the contents, and only then execute it."
        ),
        tags=("shell", "remote-download", "execution"),
    ),
    ShellExecutionRule(
        rule_id="SHELL-REVERSE-SHELL",
        title="Reverse-shell style command detected",
        pattern=re.compile(
            r"(?:\bnc\b[^\n]*\s-e\s|/dev/tcp/|\bbash\s+-i\b[^\n]*>&)",
            re.IGNORECASE,
        ),
        severity=Severity.CRITICAL,
        confidence=Confidence.HIGH,
        description=(
            "The command resembles an interactive reverse shell or outbound command channel."
        ),
        remediation=(
            "Remove the command if it is not explicitly authorized, isolate the host when "
            "appropriate, and investigate nearby files and persistence mechanisms."
        ),
        tags=("shell", "reverse-shell", "execution"),
    ),
    ShellExecutionRule(
        rule_id="SHELL-ENCODED-EXECUTION",
        title="Encoded payload decoded into a shell",
        pattern=re.compile(
            r"\bbase64\b[^|\n]*(?:-d|--decode)[^|\n]*\|\s*(?:bash|sh|zsh|ksh)\b",
            re.IGNORECASE,
        ),
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        description=(
            "An encoded value is decoded and immediately executed, obscuring the command "
            "that will run."
        ),
        remediation=(
            "Replace encoded execution with transparent, reviewed commands and verify the "
            "origin of the decoded content."
        ),
        tags=("shell", "obfuscation", "execution"),
    ),
    ShellExecutionRule(
        rule_id="SHELL-EVAL",
        title="Dynamic shell evaluation detected",
        pattern=re.compile(r"(^|[;&|]\s*|\s)eval\s+", re.IGNORECASE),
        severity=Severity.HIGH,
        confidence=Confidence.MEDIUM,
        description="The shell evaluates dynamically constructed text as executable code.",
        remediation=(
            "Avoid eval. Prefer arrays, explicit argument passing, case statements, or a "
            "narrowly scoped parser."
        ),
        tags=("shell", "dynamic-code", "execution"),
    ),
    ShellExecutionRule(
        rule_id="SHELL-NESTED-SHELL",
        title="Nested shell command execution detected",
        pattern=re.compile(r"\b(?:bash|sh|zsh|ksh)\s+-c(?:\s|$)", re.IGNORECASE),
        severity=Severity.MEDIUM,
        confidence=Confidence.MEDIUM,
        description=(
            "A nested shell executes a string command, increasing quoting and injection risk."
        ),
        remediation="Invoke the intended executable directly with explicit arguments.",
        tags=("shell", "nested-shell", "execution"),
    ),
)


def match_shell_execution_rules(
    command_line: str,
) -> list[tuple[ShellExecutionRule, re.Match[str]]]:
    """Return all dangerous-execution rule matches for one active shell line.

    Blank lines and comment-only lines are ignored here as a defensive convenience. The
    shell analyzer performs the same check before calling the rule engine.
    """

    stripped = command_line.strip()
    if not stripped or stripped.startswith("#"):
        return []

    matches: list[tuple[ShellExecutionRule, re.Match[str]]] = []
    for rule in SHELL_EXECUTION_RULES:
        for match in rule.pattern.finditer(command_line):
            matches.append((rule, match))
    return matches
