#!/usr/bin/env bash
# Look up dependency updates with Renovate, then open pull requests and refresh the dashboard.
#   scripts/renovate/run.sh [--pulls | --report-only | --dry-run]
# --pulls (default) opens/updates pull requests and the dashboard issue; --report-only refreshes the
# dashboard only; --dry-run builds the patches and prints the dashboard without touching the forge.
# Run by .forkmesh/renovate.yml; rules in docs/renovate.md.
#
# The runner has Node 22; Renovate needs Node 24, so a pinned Node is downloaded and checked against
# its sha256. Renovate and uv are pinned too (each at least two weeks old when pinned). Downloads go
# to RENOVATE_WORK_DIR (default: the job's temp directory).
set -euo pipefail

NODE_VERSION=24.22.2
NODE_SHA256=48cc0e21e048790e54c0cf5749c2725005313d652651c40b7a21feb9697aaf75 # node-v24.22.2-linux-x64.tar.xz
RENOVATE_VERSION=44.181.5
UV_VERSION=0.13.5
# V8 heap per Renovate process (see the per-folder loop below).
RENOVATE_HEAP_MB="${RENOVATE_HEAP_MB:-384}"

mode="--pulls"
case "${1:-}" in
  ""|--pulls) ;;
  --report|--report-only) mode="--report-only" ;;
  --dry-run) mode="--dry-run" ;;
  *) echo "usage: $0 [--pulls | --report-only | --dry-run]" >&2; exit 2 ;;
esac

ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
WORK="${RENOVATE_WORK_DIR:-${RUNNER_TEMP:-${TMPDIR:-/tmp}}/blt-renovate}"
mkdir -p "$WORK"

node_dir="$WORK/node-v$NODE_VERSION-linux-x64"
if [[ ! -x "$node_dir/bin/node" ]]; then
  tarball="$WORK/node-v$NODE_VERSION-linux-x64.tar.xz"
  curl -fsSL --retry 3 -o "$tarball" "https://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-linux-x64.tar.xz"
  echo "$NODE_SHA256  $tarball" | sha256sum -c --quiet
  tar -xJf "$tarball" -C "$WORK"
  rm -f "$tarball"
fi

renovate_dir="$WORK/renovate-$RENOVATE_VERSION"
if [[ ! -f "$renovate_dir/node_modules/renovate/dist/renovate.js" ]]; then
  mkdir -p "$renovate_dir"
  PATH="$node_dir/bin:$PATH" npm install --prefix "$renovate_dir" --no-audit --no-fund --ignore-scripts \
    --no-package-lock "renovate@$RENOVATE_VERSION" >/dev/null
fi

if [[ ! -x "$WORK/uv/bin/uv" ]]; then
  python3 -m venv "$WORK/uv" && "$WORK/uv/bin/pip" install -q --only-binary :all: "uv==$UV_VERSION" \
    || echo "uv $UV_VERSION could not be installed; uv.lock projects will be left out" >&2
fi

reports="$WORK/reports"
rm -rf "$reports" && mkdir -p "$reports"
# One Renovate process per project folder. A single run over the whole monorepo holds every npm
# packument it fetched (vite, wrangler and typescript are 15-40 MB of JSON each) until it ends and
# peaked near 1 GB; jobs here are capped at 700 MB with no swap. Per folder it stays near 550 MB, and
# the on-disk cache (RENOVATE_CACHE_DIR) means each registry document is still downloaded once.
mapfile -t folders < <(git -C "$ROOT" ls-files \
  | grep -E '(^|/)(package\.json|pyproject\.toml|[A-Za-z0-9_-]*requirements([-._][A-Za-z0-9_]+)?\.(txt|pip)|Cargo\.toml|pubspec\.ya?ml)$' \
  | grep -v '/node_modules/' | grep / | cut -d/ -f1 | sort -u)
echo "=== Renovate $RENOVATE_VERSION lookup (renovate.json), ${#folders[@]} folders"
failed=()
# The job installs Renovate with --ignore-scripts, so the optional re2 addon is never built and every
# Renovate process warns "RE2 not usable, falling back to RegExp" with a 30-line stack trace. The
# fallback is fine; drop that warning (its indented lines included) so the log shows what matters.
drop_re2_warning() {
  awk '/^ WARN: RE2 not usable/ { skip = 1; next } skip && /^  / { next } { skip = 0; print; fflush() }'
}
n=0
for folder in "${folders[@]}"; do
  n=$((n + 1))
  echo "--- $folder ($n/${#folders[@]})"
  if ! (
    cd "$ROOT"
    export LOG_LEVEL="${LOG_LEVEL:-warn}"
    export RENOVATE_PLATFORM=local RENOVATE_REPORT_TYPE=file RENOVATE_REPORT_PATH="$reports/$folder.json"
    export RENOVATE_BASE_DIR="$WORK/base" RENOVATE_CACHE_DIR="$WORK/cache"
    export RENOVATE_ONBOARDING=false RENOVATE_REQUIRE_CONFIG=required
    export RENOVATE_FORCE="{\"includePaths\":[\"$folder/**\"]}"
    # One npm request at a time and no in-memory HTTP cache keep the peak down; the malloc
    # thresholds hand the big response buffers back to the system instead of keeping them.
    export RENOVATE_X_DISABLE_HTTP_MEMCACHE=1 MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536
    export RENOVATE_HOST_RULES='[{"matchHost":"registry.npmjs.org","concurrentRequestLimit":1},{"matchHost":"pypi.org","concurrentRequestLimit":4}]'
    # Changelog and GitHub-hosted lookups; without it they hit the anonymous rate limit.
    if [[ -n "${GH_API_TOKEN:-}" ]]; then export RENOVATE_GITHUB_COM_TOKEN="$GH_API_TOKEN"; fi
    unset GITHUB_TOKEN FORKMESH_TOKEN BLT_RENOVATE_SEED GH_API_TOKEN
    "$node_dir/bin/node" --max-old-space-size="$RENOVATE_HEAP_MB" --max-semi-space-size=4 \
      "$renovate_dir/node_modules/renovate/dist/renovate.js" 2>&1
  ) | drop_re2_warning; then
    echo "--- $folder: Renovate failed" >&2
    failed+=(--failed "$folder")
  fi
done

echo "=== Apply updates ($mode)"
report_args=()
for f in "$reports"/*.json; do [[ -e "$f" ]] && report_args+=(--report "$f"); done
UV_BIN="$( [[ -x "$WORK/uv/bin/uv" ]] && echo "$WORK/uv/bin/uv" || true )" \
  node "$ROOT/scripts/renovate/apply.mjs" "${report_args[@]}" "${failed[@]}" --work "$WORK" "$mode"
