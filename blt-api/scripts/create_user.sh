#!/bin/bash
# Create a user via BLT API.
set -euo pipefail

API_BASE="${API_BASE:-https://api.owaspblt.org/v2}"
USERNAME=""
EMAIL=""
PASSWORD=""
DESCRIPTION=""

rand_suffix() {
    date +%s%N | tail -c 7
}

make_username() {
    echo "bltuser$(rand_suffix)"
}

make_email() {
    echo "test+$(rand_suffix)@owaspblt.org"
}

make_password() {
    # Strong default password satisfying uppercase/lowercase/number/symbol requirements.
    echo "Blt!$(rand_suffix)Secure9"
}

make_description() {
    echo "Auto-generated account created by scripts/create_user.sh"
}

usage() {
    cat <<'EOF'
Usage:
    bash scripts/create_user.sh [-u <username>] [-e <email>] [-p <password>] [-d <description>] [--api-base <url>]

Examples:
    bash scripts/create_user.sh
  bash scripts/create_user.sh -u alice -e alice@example.com -p 'S3cure!Passw0rd'
  bash scripts/create_user.sh -u bob -e bob@example.com --api-base https://api.owaspblt.org/v2

Environment override:
  API_BASE=https://api.owaspblt.org/v2 bash scripts/create_user.sh -u alice -e alice@example.com
EOF
}

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Error: '$1' is required but not installed." >&2
        exit 1
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -u|--username)
            USERNAME="${2:-}"
            shift 2
            ;;
        -e|--email)
            EMAIL="${2:-}"
            shift 2
            ;;
        -p|--password)
            PASSWORD="${2:-}"
            shift 2
            ;;
        -d|--description)
            DESCRIPTION="${2:-}"
            shift 2
            ;;
        --api-base)
            API_BASE="${2:-}"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            exit 1
            ;;
    esac
done

if [[ -z "$USERNAME" ]]; then
    USERNAME="$(make_username)"
fi

if [[ -z "$EMAIL" ]]; then
    EMAIL="$(make_email)"
fi

if [[ -z "$PASSWORD" ]]; then
    PASSWORD="$(make_password)"
fi

if [[ -z "$DESCRIPTION" ]]; then
    DESCRIPTION="$(make_description)"
fi

require_cmd curl
require_cmd jq

API_BASE="${API_BASE%/}"
ENDPOINT="$API_BASE/users"

PAYLOAD=$(jq -n \
    --arg username "$USERNAME" \
    --arg email "$EMAIL" \
    --arg password "$PASSWORD" \
    --arg description "$DESCRIPTION" \
    '{username: $username, email: $email, password: $password, description: $description}')

echo "Creating user with:"
echo "  username=$USERNAME"
echo "  email=$EMAIL"
echo "  description=$DESCRIPTION"

TMP_FILE=$(mktemp)
trap 'rm -f "$TMP_FILE"' EXIT

STATUS_CODE=$(curl -sS -o "$TMP_FILE" -w "%{http_code}" \
    -X POST "$ENDPOINT" \
    -H "Content-Type: application/json" \
    --data "$PAYLOAD")

echo "POST $ENDPOINT"
echo "Status: $STATUS_CODE"
cat "$TMP_FILE"
echo ""

if [[ "$STATUS_CODE" -lt 200 || "$STATUS_CODE" -ge 300 ]]; then
    exit 1
fi
