#!/usr/bin/env bash
# Commit data files a workflow regenerated and push them back (needs `permissions: contents: write`).
#
#   scripts/actions/commit-back.sh -m "<project>: <message>" [-b main] [--deploy <project>] [--rebuild <command>] -- <path>...
#
# Paths are relative to the current directory. Only those paths are staged (deletions included);
# nothing is committed when they did not change. The commit is rebased onto origin/<branch> and
# pushed with a few retries. On a conflict in those regenerated files the rebase keeps this run's
# output (-X theirs), so a newer run never fails because an older one already pushed. The runner sets the bot identity, so none is configured here.
# --deploy runs scripts/deploy.sh <project> after a successful push when CLOUDFLARE_API_TOKEN is set,
# because pushes made by a workflow do not trigger other push workflows (.forkmesh/deploy.yml).
# --rebuild is for files that other writers append to, such as the .forkmesh/issues ledgers, where
# "-X theirs" would drop the other side's events: when the push is refused, the checkout moves to
# origin/<branch> (git reset --keep), <command> (a fixed command from the workflow, run with bash -c)
# writes the paths again from that state, and the new result is committed and pushed.
set -euo pipefail

message=""; branch="main"; deploy=""; rebuild=""; paths=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -m) message="$2"; shift 2 ;;
    -b) branch="$2"; shift 2 ;;
    --deploy) deploy="$2"; shift 2 ;;
    --rebuild) rebuild="$2"; shift 2 ;;
    --) shift; paths+=("$@"); break ;;
    *) paths+=("$1"); shift ;;
  esac
done
[[ -n "$message" && ${#paths[@]} -gt 0 ]] || { sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }

stage() {
  for p in "${paths[@]}"; do
    # Skip paths that neither exist nor are tracked (git add would fail on them).
    if [[ -e "$p" ]] || [[ -n "$(git ls-files -- "$p")" ]]; then
      git add -A -- "$p"
    fi
  done
}
stage
if git diff --cached --quiet; then
  echo "commit-back: no changes in ${paths[*]}"
  exit 0
fi
git commit -q -m "$message"
git --no-pager show --stat --format='%h %s' HEAD

pushed=0
if [[ -n "$rebuild" ]]; then
  for attempt in 1 2 3 4 5; do
    if git push origin "HEAD:$branch"; then pushed=1; break; fi
    echo "commit-back: push attempt $attempt refused, rebuilding on origin/$branch" >&2
    sleep $((attempt * 2))
    git fetch -q origin "$branch"
    git reset -q --keep FETCH_HEAD
    bash -c "$rebuild"
    stage
    if git diff --cached --quiet; then
      echo "commit-back: nothing left to commit after rebuilding on origin/$branch"
      exit 0
    fi
    git commit -q -m "$message"
  done
fi
for attempt in 1 2 3 4 5; do
  [[ $pushed -eq 1 || -n "$rebuild" ]] && break
  if git pull -q --rebase -X theirs --autostash origin "$branch" && git push origin "HEAD:$branch"; then
    pushed=1; break
  fi
  git rebase --abort >/dev/null 2>&1 || true
  echo "commit-back: push attempt $attempt failed, retrying" >&2
  sleep $((attempt * 5))
done
[[ $pushed -eq 1 ]] || { echo "commit-back: could not push to $branch" >&2; exit 1; }

if [[ -n "$deploy" ]]; then
  if [[ -n "${CLOUDFLARE_API_TOKEN:-}" ]]; then
    "$(git rev-parse --show-toplevel)/scripts/deploy.sh" "$deploy"
  else
    echo "commit-back: CLOUDFLARE_API_TOKEN not set, skipping deploy of $deploy"
  fi
fi
