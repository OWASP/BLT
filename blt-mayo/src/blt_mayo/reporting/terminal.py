from __future__ import annotations

from rich.console import Console
from rich.table import Table

from blt_mayo.models.scan import ScanResult


def render_terminal(result: ScanResult, console: Console | None = None) -> None:
    console = console or Console()
    console.print("[bold]BLT-MAYO scan complete[/bold]")
    console.print(
        f"Artifacts: [cyan]{len(result.artifacts)}[/cyan]  "
        f"Findings: [yellow]{len(result.findings)}[/yellow]  "
        f"Observations: [magenta]{len(result.observations)}[/magenta]"
    )
    table = Table(show_lines=True)
    table.add_column("Severity")
    table.add_column("Rule")
    table.add_column("Finding")
    table.add_column("Artifact")
    table.add_column("Evidence")
    for finding in result.findings:
        table.add_row(
            finding.severity.value.upper(),
            finding.rule_id,
            finding.title,
            str(finding.artifact_path),
            finding.evidence.summary,
        )
    console.print(table)
