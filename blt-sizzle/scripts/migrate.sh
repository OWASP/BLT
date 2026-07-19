#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/migrate.sh dev [wrangler-options]
  bash scripts/migrate.sh prod [wrangler-options]

Modes:
  dev       Apply D1 migrations to the local development database with --local.
  prod      Apply D1 migrations to the remote production database with --remote.

Environment:
  D1_DATABASE                 Database name to migrate. Defaults to sizzle-db.
  CONFIRM_PROD_MIGRATION=1    Required for prod migrations.

Examples:
  bash scripts/migrate.sh dev
  D1_DATABASE=sizzle-db bash scripts/migrate.sh dev
  CONFIRM_PROD_MIGRATION=1 bash scripts/migrate.sh prod
USAGE
}

mode="${1:-dev}"
if [[ "$mode" == "-h" || "$mode" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -gt 0 ]]; then
  shift
fi

D1_DATABASE="${D1_DATABASE:-sizzle-db}"

case "$mode" in
  dev|development|local)
    target_label="local development"
    target_flag="--local"
    ;;
  prod|production|remote)
    target_label="remote production"
    target_flag="--remote"
    if [[ "${CONFIRM_PROD_MIGRATION:-}" != "1" ]]; then
      echo "Refusing to run production migrations without confirmation." >&2
      echo "Run with CONFIRM_PROD_MIGRATION=1 after checking wrangler.toml and the target account." >&2
      exit 3
    fi
    ;;
  *)
    echo "Unknown migration target: $mode" >&2
    echo >&2
    usage >&2
    exit 2
    ;;
esac

cmd=(npx wrangler d1 migrations apply "$D1_DATABASE" "$target_flag" "$@")

echo "Applying D1 migrations to $target_label database '$D1_DATABASE'..."
printf '+ %q ' "${cmd[@]}"
echo

exec "${cmd[@]}"
