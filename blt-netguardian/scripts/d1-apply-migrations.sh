#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
wrangler d1 migrations apply blt-netguardian --local
echo "Applied migrations/ (0001 legacy scanner, 0002 ingest core) to local D1."
