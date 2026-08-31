#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
public_dir="$repo_dir/public"
mkdir -p "$public_dir"

for path in CNAME favicon.ico README.md logo.png index.html gsoc2026.html mentor-guide.html pr-report.html progress-tracker.html css data images js blog; do
  if [[ -d "$repo_dir/$path" ]]; then
    mkdir -p "$public_dir/$path"
    cp -a "$repo_dir/$path/." "$public_dir/$path/"
  elif [[ -f "$repo_dir/$path" ]]; then
    cp "$repo_dir/$path" "$public_dir/$path"
  fi
done

echo "Built safe static output in $public_dir"
