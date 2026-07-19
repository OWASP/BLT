from __future__ import annotations

import json
import platform
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from blt_mayo import __version__
from blt_mayo.config.loader import ConfigError, load_config
from blt_mayo.reporting.json_report import write_json_report
from blt_mayo.reporting.terminal import render_terminal
from blt_mayo.scanner.orchestrator import ScanOrchestrator

app = typer.Typer(
    name="blt-mayo",
    help="Linux security auditing and dangerous shell-script analysis workflow.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def scan(
    paths: Annotated[list[Path] | None, typer.Argument(help="Files or directories to scan")] = None,
    config: Annotated[
        Path | None, typer.Option("--config", "-c", help="YAML configuration file")
    ] = None,
    profile: Annotated[str | None, typer.Option(help="quick, standard, deep, or policy")] = None,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write a JSON report")
    ] = None,
    follow_symlinks: Annotated[
        bool | None, typer.Option("--follow-symlinks/--no-follow-symlinks")
    ] = None,
) -> None:
    """Scan Linux files and emit normalized findings."""
    overrides = {"profile": profile, "follow_symlinks": follow_symlinks}
    try:
        scan_config = load_config(config, overrides=overrides)
    except ConfigError as exc:
        raise typer.BadParameter(str(exc)) from exc
    roots = paths or scan_config.include_paths
    if not roots:
        raise typer.BadParameter("Provide a path argument or include_paths in the config file")
    result = ScanOrchestrator(scan_config).scan(roots)
    render_terminal(result, console)
    if output:
        report_path = write_json_report(result, output)
        console.print(f"JSON report: [bold]{report_path}[/bold]")


@app.command()
def report(
    report_file: Annotated[Path, typer.Argument(help="Existing BLT-MAYO JSON report")],
) -> None:
    """Render a concise summary from a saved JSON report."""
    data = json.loads(report_file.read_text(encoding="utf-8"))
    summary = data.get("summary", {})
    console.print(f"[bold]Findings:[/bold] {summary.get('findings', 0)}")
    for finding in data.get("findings", []):
        console.print(
            f"[{finding.get('severity', 'info').upper()}] {finding.get('rule_id')}: "
            f"{finding.get('title')} — {finding.get('artifact_path')}"
        )


def _planned(name: str, planned_week: str) -> None:
    console.print(f"[yellow]{name} is scaffolded and planned for {planned_week}.[/yellow]")


@app.command()
def compare() -> None:
    """Compare scan state (implementation scheduled after Week 3)."""
    _planned("compare", "Week 9")


@app.command()
def review() -> None:
    """Review findings (implementation scheduled after Week 3)."""
    _planned("review", "Week 10")


@app.command()
def bundle() -> None:
    """Bundle correlated findings (implementation scheduled after Week 3)."""
    _planned("bundle", "Week 8")


@app.command()
def export() -> None:
    """Export reviewed findings (implementation scheduled after Week 3)."""
    _planned("export", "Week 11")


@app.command(name="blt-submit")
def blt_submit() -> None:
    """Submit a reviewed BLT draft (implementation scheduled after Week 3)."""
    _planned("blt-submit", "Week 11")


@app.command()
def doctor() -> None:
    """Check the local runtime and core dependencies."""
    checks = {
        "blt_mayo_version": __version__,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "filesystem_encoding": sys.getfilesystemencoding(),
    }
    console.print("[bold green]BLT-MAYO doctor[/bold green]")
    for key, value in checks.items():
        console.print(f"{key}: {value}")


def main() -> None:
    app()
