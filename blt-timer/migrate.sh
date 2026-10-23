#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: ./migrate.sh dev|prod [--dry-run]

Apply Cloudflare D1 migrations for BLT Timer Web.

Targets:
  dev       Apply migrations to the local D1 database used by wrangler dev
  prod      Apply migrations to the remote production D1 database

Examples:
  ./migrate.sh dev
  ./migrate.sh prod
  ./migrate.sh dev --dry-run

Notes:
  - dev uses:  npx wrangler d1 migrations apply DB --local
  - prod uses: npx wrangler d1 migrations apply DB --remote --env production
  - set BLT_D1_PERSIST_TO to use an isolated local D1 directory
USAGE
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage >&2
  exit 2
fi

TARGET="$1"
DRY_RUN="${2:-}"

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

PERSIST_ARGS=()

if [[ -n "${BLT_D1_PERSIST_TO:-}" ]]; then
  PERSIST_ARGS=(--persist-to "$BLT_D1_PERSIST_TO")
fi

case "$TARGET" in
  dev)
    run npx wrangler d1 migrations apply DB --local "${PERSIST_ARGS[@]}"
    ;;
  prod)
    run npx wrangler d1 migrations apply DB --remote --env production
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
