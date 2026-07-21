#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: ./deploy.sh [--dry-run]

Apply production D1 migrations and deploy BLT Timer Web.

One-time prerequisites:
  - Create and configure the production D1 database in wrangler.toml.
  - Set SESSION_SECRET with: npx wrangler secret put SESSION_SECRET --env production
USAGE
}

if [[ $# -gt 1 || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

DRY_RUN="${1:-}"

if [[ -n "$DRY_RUN" && "$DRY_RUN" != "--dry-run" ]]; then
  usage >&2
  exit 2
fi

run() {
  if [[ "$DRY_RUN" == "--dry-run" ]]; then
    printf 'DRY RUN:'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

run ./migrate.sh prod
run npx wrangler deploy --env production
