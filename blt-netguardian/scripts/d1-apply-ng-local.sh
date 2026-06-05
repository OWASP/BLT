#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
wrangler d1 execute blt-netguardian --local --file=migrations/ng/0001_core.sql
echo "Applied migrations/ng/0001_core.sql to local D1 (blt-netguardian)."
