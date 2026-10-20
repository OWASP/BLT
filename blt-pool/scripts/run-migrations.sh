#!/usr/bin/env bash
set -euo pipefail

npx wrangler d1 migrations apply LEADERBOARD_DB --remote
