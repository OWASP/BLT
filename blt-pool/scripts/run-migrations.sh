#!/usr/bin/env bash
set -euo pipefail

wrangler d1 migrations apply LEADERBOARD_DB --remote
