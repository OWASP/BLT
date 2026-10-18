#!/usr/bin/env bash
# Packages the extension into dist/blt-extension-<version>.zip and uploads it to the Chrome Web Store.
#
#   scripts/release-chrome.sh [--package-only] [--no-publish]
#
# Needs CHROME_CLIENT_ID, CHROME_CLIENT_SECRET and CHROME_REFRESH_TOKEN (Google OAuth client with the
# chromewebstore scope). Run by .forkmesh/blt-extension--release.yml; replaces the GitHub workflows
# create-release.yaml (zip packaging) and release.yaml (mnao305/chrome-extension-upload).
set -euo pipefail
cd "$(dirname "$0")/.."

EXTENSION_ID="${CHROME_EXTENSION_ID:-bififchikfckcnblimmncopjinfgccme}"
package_only=0; publish=1
for arg in "$@"; do
  case "$arg" in
    --package-only) package_only=1 ;;
    --no-publish) publish=0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

version=$(python3 -c 'import json; print(json.load(open("manifest.json"))["version"])')
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
# Same file set as the old create-release workflow.
cp manifest.json "$stage/"
cp ./*.js ./*.html ./*.css LICENSE "$stage/" 2>/dev/null || true
for d in img libs _locales toolbar_res; do [[ -d $d ]] && cp -r "$d" "$stage/"; done
rm -f "$stage/jest.config.js"
mkdir -p dist
zip="$PWD/dist/blt-extension-$version.zip"
rm -f "$zip"
(cd "$stage" && python3 -c 'import os, sys, zipfile
with zipfile.ZipFile(sys.argv[1], "w", zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk("."):
        for f in sorted(files):
            p = os.path.join(root, f)
            z.write(p, os.path.relpath(p, "."))' "$zip")
echo "packaged $zip"
[[ $package_only -eq 1 ]] && exit 0

: "${CHROME_CLIENT_ID:?CHROME_CLIENT_ID is required}"
: "${CHROME_CLIENT_SECRET:?CHROME_CLIENT_SECRET is required}"
: "${CHROME_REFRESH_TOKEN:?CHROME_REFRESH_TOKEN is required}"

access_token=$(curl -fsS https://oauth2.googleapis.com/token \
  --data-urlencode "client_id=$CHROME_CLIENT_ID" \
  --data-urlencode "client_secret=$CHROME_CLIENT_SECRET" \
  --data-urlencode "refresh_token=$CHROME_REFRESH_TOKEN" \
  --data-urlencode "grant_type=refresh_token" | jq -r '.access_token // empty')
[[ -n "$access_token" ]] || { echo "could not get a Chrome Web Store access token" >&2; exit 1; }
auth=(-H "Authorization: Bearer $access_token" -H "x-goog-api-version: 2")

upload=$(curl -sS -X PUT "${auth[@]}" -T "$zip" \
  "https://www.googleapis.com/upload/chromewebstore/v1.1/items/$EXTENSION_ID")
echo "upload: $(jq -c '{uploadState, itemError}' <<<"$upload")"
[[ "$(jq -r '.uploadState' <<<"$upload")" == "SUCCESS" ]] || exit 1

if [[ $publish -eq 1 ]]; then
  result=$(curl -sS -X POST "${auth[@]}" -H "Content-Length: 0" \
    "https://www.googleapis.com/chromewebstore/v1.1/items/$EXTENSION_ID/publish")
  echo "publish: $(jq -c '{status, statusDetail}' <<<"$result")"
  jq -e '.status | index("OK")' >/dev/null <<<"$result" || exit 1
fi
