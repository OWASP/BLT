"""
formatter.py

GitLab Merge Request advisory formatter.

Responsibilities
----------------
- Format advisories as GitLab Markdown
- Format fallback advisories
- Format references
- Format metadata
- Keep presentation separate from business logic

This module does not communicate with GitLab.
"""

from __future__ import annotations

from typing import Any


SEVERITY_EMOJIS = {
    "Critical": "🛑",
    "High": "🔴",
    "Medium": "🟠",
    "Low": "🟡",
    "Info": "🔵",
}


class GitLabAdvisoryFormatter:
    """
    Formats advisories into GitLab Flavored Markdown.
    """

    @staticmethod
    def format(
        advisory: dict[str, Any],
    ) -> str:
        """
        Convert an advisory dictionary into
        GitLab Markdown.
        """

        severity = advisory.get("severity", "Info")

        emoji = SEVERITY_EMOJIS.get(
            severity,
            "🔵",
        )

        lines: list[str] = []

        lines.append("# 🔐 BLT Preflight Security Advisory")
        lines.append("")

        lines.append(
            f"**Severity:** {emoji} **{severity}**"
        )

        category = advisory.get("category")

        if category:
            lines.append(
                f"**Category:** {category}"
            )

        title = advisory.get("title")

        if title:
            lines.append(
                f"**Title:** {title}"
            )

        lines.append("")

        explanation = advisory.get(
            "explanation",
            "",
        )

        if explanation:
            lines.append("## Explanation")
            lines.append("")
            lines.append(explanation)
            lines.append("")

        recommendation = advisory.get(
            "recommendation",
            "",
        )

        if recommendation:
            lines.append("## Recommendation")
            lines.append("")
            lines.append(recommendation)
            lines.append("")

        references = advisory.get(
            "references",
            [],
        )

        if references:
            lines.append("## References")
            lines.append("")

            for reference in references:
                lines.append(f"- {reference}")

            lines.append("")

        metadata = advisory.get(
            "metadata",
            {},
        )

        if metadata:

            lines.append("<details>")
            lines.append("<summary>Pipeline Metadata</summary>")
            lines.append("")

            for key, value in metadata.items():
                lines.append(
                    f"- **{key}**: `{value}`"
                )

            lines.append("")
            lines.append("</details>")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append(
            "_Generated automatically by BLT Preflight._"
        )

        return "\n".join(lines)

    @staticmethod
    def format_error(
        message: str,
    ) -> str:
        """
        Format pipeline errors.
        """

        return "\n".join(
            [
                "# ⚠️ BLT Preflight",
                "",
                "The advisory pipeline could not generate",
                "a security advisory.",
                "",
                f"**Reason:** {message}",
            ]
        )

    @staticmethod
    def format_fallback(
        advisory: dict[str, Any],
    ) -> str:
        """
        Format deterministic fallback advisories.
        """

        markdown = GitLabAdvisoryFormatter.format(
            advisory
        )

        notice = (
            "> **Note**\n"
            "> This advisory was generated using the "
            "fallback pipeline because the primary "
            "advisory generation could not complete.\n\n"
        )

        return notice + markdown