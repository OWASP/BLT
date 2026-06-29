#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Usage: $0 dev|prod

Apply Cloudflare D1 migrations for BLT Newsletter.

  dev   Apply migrations to the local D1 database
  prod  Apply migrations to the remote production D1 database
USAGE
}

if [[ $# -ne 1 ]]; then
  usage >&2
  exit 2
fi

case "$1" in
  dev)
    wrangler d1 migrations apply blt-newsletter --local
    ;;
  prod)
    wrangler d1 migrations apply blt-newsletter --remote
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
