#!/usr/bin/env bash
# Fails if runtime DDL appears in Python sources.
set -euo pipefail

SEARCH_DIRS=("src")
VIOLATION_PATTERN='(^|[^[:alnum:]_])(create[[:space:]]+table|alter[[:space:]]+table|drop[[:space:]]+table)([^[:alnum:]_]|$)'
IGNORE_COMMENT_PATTERN='^[[:space:]]*#'

found=0

for dir in "${SEARCH_DIRS[@]}"; do
    while IFS= read -r -d '' file; do
        while IFS= read -r line; do
            if echo "$line" | grep -qE "$IGNORE_COMMENT_PATTERN"; then
                continue
            fi

            if echo "$line" | grep -qiE "$VIOLATION_PATTERN"; then
                if echo "$line" | grep -qE "['\"]"; then
                    echo "VIOLATION in $file: $line"
                    found=1
                fi
            fi
        done < "$file"
    done < <(find "$dir" -name "*.py" -print0)
done

if [ "$found" -eq 1 ]; then
    echo ""
    echo "ERROR: Runtime DDL detected in source files."
    echo "Move schema changes into SQL files under migrations/."
    exit 1
fi

echo "OK: No runtime DDL found in source files."
