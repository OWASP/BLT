#!/usr/bin/env bash
# Run one or more projects' tests:  scripts/ci/test.sh <project>... | --all | --changed <base-ref>
# Commands live in scripts/ci/tests.tsv. Python projects get a fresh virtualenv each run.
set -uo pipefail

ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
TABLE="$ROOT/scripts/ci/tests.tsv"
WORK="${CI_WORK_DIR:-${RUNNER_TEMP:-${TMPDIR:-/tmp}}/blt-ci}"
mkdir -p "$WORK"

projects=()
case "${1:-}" in
  --all) mapfile -t projects < <(grep -v '^#' "$TABLE" | cut -f1) ;;
  --changed)
    # An empty or all-zero base (new branch, first push) tests nothing.
    base="${2:-}"
    if [[ -z "$base" || "$base" =~ ^0+$ ]]; then echo "no base commit; nothing to test"; exit 0; fi
    if ! git -C "$ROOT" cat-file -e "$base^{commit}" 2>/dev/null; then
      echo "base commit $base not found; nothing to test (run with --all or project names)" >&2; exit 0
    fi
    mapfile -t changed < <(git -C "$ROOT" diff --name-only "$base"...HEAD | cut -d/ -f1 | sort -u)
    for p in $(grep -v '^#' "$TABLE" | cut -f1); do
      [[ " ${changed[*]} " == *" $p "* ]] && projects+=("$p")
    done ;;
  ""|-h|--help) sed -n '2,3p' "${BASH_SOURCE[0]}" | sed 's/^# //'; exit 2 ;;
  *) projects=("$@") ;;
esac
[[ ${#projects[@]} -eq 0 ]] && { echo "no projects to test"; exit 0; }

# Suites too big for a small runner. On a machine with under 3 GB of memory (the git.owaspblt.org
# runner shares 1 GB with the website) they are skipped in --changed/--all runs, so they can't
# push the site into swap; name them explicitly to run them anyway.
HEAVY=(blt-core)
mem_kb="$(awk '/^MemTotal:/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)"
low_memory=0; [[ "${mem_kb:-0}" -gt 0 && "${mem_kb}" -lt 3000000 ]] && low_memory=1

passed=(); failed=(); skipped=()
for p in "${projects[@]}"; do
  line="$(awk -F'\t' -v p="$p" '$1==p' "$TABLE")"
  [[ -z "$line" ]] && { echo "unknown project: $p" >&2; failed+=("$p"); continue; }
  tool="$(cut -f2 <<<"$line")"; cmd="$(cut -f3- <<<"$line")"
  if [[ $low_memory -eq 1 && ( "${1:-}" == "--changed" || "${1:-}" == "--all" ) && " ${HEAVY[*]} " == *" $p "* ]]; then
    echo "--- $p: SKIPPED (heavy suite; under 3 GB of memory here)"; skipped+=("$p"); continue
  fi
  if ! command -v "$( [[ $tool == python ]] && echo python3 || ([[ $tool == rust ]] && echo cargo) || echo "$tool")" >/dev/null; then
    echo "--- $p: SKIPPED ($tool not installed)"; skipped+=("$p"); continue
  fi
  echo "=== $p ($tool): $cmd"
  log="$WORK/$p.log"
  (
    cd "$ROOT/$p" || exit 1
    npm_install() { if [[ -f package-lock.json ]]; then npm ci --no-audit --no-fund; else npm install --no-audit --no-fund; fi; }
    export -f npm_install
    if [[ $tool == python ]]; then
      python3 -m venv "$WORK/venv-$p" && . "$WORK/venv-$p/bin/activate" && python -m pip install -q --upgrade "pip>=25.1" || exit 1
    fi
    bash -c "$cmd"
  ) >"$log" 2>&1
  if [[ $? -eq 0 ]]; then echo "--- $p: PASS"; passed+=("$p")
  else echo "--- $p: FAIL (log: $log)"; tail -n 15 "$log" | sed 's/^/    /'; failed+=("$p"); fi
done

echo
echo "passed:  ${#passed[@]} ${passed[*]}"
echo "failed:  ${#failed[@]} ${failed[*]}"
echo "skipped: ${#skipped[@]} ${skipped[*]}"
[[ ${#failed[@]} -eq 0 ]]
