# Shell Dangerous-Execution Analyzer

## Purpose

It inspects shell source files as text and creates normalized security findings for high-signal dangerous-execution patterns.

The analyzer is deliberately independent from Python AST analysis. Python, cron, systemd, startup-hook, and SSH analyzers are outside this PR.

## Workflow

```text
Filesystem traversal
        ↓
Metadata extraction and artifact classification
        ↓
ShellScriptAnalyzer receives shell_script artifacts
        ↓
Read source as UTF-8 text with replacement for invalid bytes
        ↓
Skip blank lines and comment-only lines
        ↓
Run reusable shell execution rules on each active line
        ↓
Create normalized Finding objects
        ↓
Terminal and JSON reporting
```

The inspected file is never sourced, imported, executed, or modified.

## Implemented rules

| Rule ID | Detection | Base severity | Confidence |
|---|---|---:|---:|
| `SHELL-PIPE-TO-SHELL` | `curl` or `wget` piped to `bash`, `sh`, `zsh`, or `ksh` | Critical | High |
| `SHELL-REVERSE-SHELL` | Common reverse-shell command forms | Critical | High |
| `SHELL-ENCODED-EXECUTION` | Base64 decoding piped to a shell | High | High |
| `SHELL-EVAL` | Dynamic shell `eval` | High | Medium |
| `SHELL-NESTED-SHELL` | A shell invoked with `-c` | Medium | Medium |

## Severity and confidence

Severity describes the potential impact. Confidence describes how strongly the text matches the stated behavior. They remain separate fields.

The analyzer increases severity by one level when a match appears in a high- or critical-sensitivity path. Severity is capped at `critical`.

## Evidence policy

Each finding stores only:

- the source line number;
- a one-line normalized snippet;
- an explanation and remediation;
- relevant metadata such as owner and permissions.

The entire source file is not copied into the finding.

## Known limitations

This first implementation uses high-signal regular expressions rather than a complete shell parser. It can miss heavily obfuscated or multiline constructs and may require later tuning for unusual quoting. Human review remains part of the intended workflow.

## Run the tests

```bash
pytest tests/test_shell_execution_rules.py tests/test_shell_script_analyzer.py -v
```

Run the full acceptance path:

```bash
scripts/run_shell_acceptance.sh
```

## Scope boundary

Included:

- reusable shell rule definitions;
- shell-file analysis;
- normalized findings;
- fixtures, unit tests, integration tests, CI, and documentation.

Not included:

- Python AST analysis;
- cron, systemd, startup-hook, or SSH analysis;
- automatic remediation;
- execution of inspected content.
