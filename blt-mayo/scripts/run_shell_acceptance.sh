#!/usr/bin/env bash

set -euo pipefail

REPORT_FILE="shell-scan-report.json"
trap 'rm -f "$REPORT_FILE"' EXIT

ruff check src tests
python -m compileall -q \
  src \
  tests/test_shell_execution_rules.py \
  tests/test_shell_script_analyzer.py \
  tests/test_orchestrator_reporting.py \
  tests/conftest.py

pytest \
  tests/test_shell_execution_rules.py \
  tests/test_shell_script_analyzer.py \
  tests/test_orchestrator_reporting.py \
  -v

PYTHONPATH=src python -m blt_mayo scan tests/fixtures/shell --output "$REPORT_FILE"

test -s "$REPORT_FILE"
echo "Shell analyzer acceptance test passed."
