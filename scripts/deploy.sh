#!/usr/bin/env bash
# Deploy BLT projects to Cloudflare from this repo.
#
#   scripts/deploy.sh <project> [<project>...]   deploy one or more projects
#   scripts/deploy.sh --all                      deploy every project in scripts/deploy/projects.tsv
#   scripts/deploy.sh --list                     show the deploy table
#   add --dry-run to build and validate without publishing
#
# Needs CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID (or a `wrangler login` session).
# Per-project settings (folder, deploy type, extra args, build step) live in scripts/deploy/projects.tsv.
set -euo pipefail

ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
TABLE="$ROOT/scripts/deploy/projects.tsv"
WRANGLER="${WRANGLER:-npx --yes wrangler@4}"
DRY_RUN=0
ALL=0
TARGETS=()

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --all) ALL=1 ;;
    --list) grep -v '^#' "$TABLE" | column -t -s $'\t'; exit 0 ;;
    -h|--help) sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "unknown option: $arg" >&2; exit 2 ;;
    *) TARGETS+=("$arg") ;;
  esac
done
if [[ $ALL -eq 0 && ${#TARGETS[@]} -eq 0 ]]; then
  echo "usage: scripts/deploy.sh <project>... | --all | --list  [--dry-run]" >&2
  exit 2
fi

deploy_one() {
  local project="$1" dir="$2" type="$3" args="$4" prebuild="$5"
  [[ "$args" == "-" ]] && args=""
  [[ "$prebuild" == "-" ]] && prebuild=""
  echo "==> $project ($type) in $dir"
  (
    cd "$ROOT/$dir"
    if [[ -n "$prebuild" ]]; then
      echo "    build: $prebuild"
      bash -c "$prebuild"
    fi
    case "$type" in
      worker)
        if [[ $DRY_RUN -eq 1 ]]; then $WRANGLER deploy $args --dry-run --outdir "$(mktemp -d)"
        else $WRANGLER deploy $args; fi ;;
      pages)
        local name out
        name="$(sed -n 's/^name *= *"\(.*\)"/\1/p' wrangler.toml | head -n1)"
        out="$(sed -n 's/^pages_build_output_dir *= *"\(.*\)"/\1/p' wrangler.toml | head -n1)"
        if [[ $DRY_RUN -eq 1 ]]; then
          [[ -d "$out" ]] || { echo "    missing output dir $out" >&2; exit 1; }
          echo "    would run: wrangler pages deploy $out --project-name $name --branch main"
        else $WRANGLER pages deploy "$out" --project-name "$name" --branch main; fi ;;
      pywrangler)
        if [[ $DRY_RUN -eq 1 ]]; then uv run pywrangler deploy --dry-run --outdir "$(mktemp -d)"
        else uv run pywrangler deploy; fi ;;
      script)
        if [[ $DRY_RUN -eq 1 ]]; then echo "    would run: $args"
        else bash -c "$args"; fi ;;
      *) echo "    unknown deploy type: $type" >&2; exit 1 ;;
    esac
  )
}

failed=()
found=0
while IFS=$'\t' read -r -u 3 project dir type args prebuild; do
  [[ -z "$project" || "$project" == \#* ]] && continue
  if [[ $ALL -eq 1 || " ${TARGETS[*]} " == *" $project "* ]]; then
    found=$((found + 1))
    deploy_one "$project" "$dir" "$type" "$args" "$prebuild" || failed+=("$project")
  fi
done 3< "$TABLE"

if [[ $ALL -eq 0 && $found -ne ${#TARGETS[@]} ]]; then
  echo "unknown project(s); run scripts/deploy.sh --list" >&2
  exit 2
fi
if [[ ${#failed[@]} -gt 0 ]]; then
  echo "FAILED: ${failed[*]}" >&2
  exit 1
fi
echo "done: $found project(s)"
