#!/bin/bash

# BLT-Leaf Local Development Setup Script
echo "🍃 BLT-Leaf Local Setup"
echo "========================"

# Check wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo "❌ Wrangler not found. Install it with: npm install -g wrangler"
    exit 1
fi

# Login check
echo ""
echo "📋 Step 1: Checking Cloudflare login..."
wrangler whoami 2>/dev/null || wrangler login

DB_NAME="pr_tracker"
echo
echo "📋 Step 2: Creating or locating D1 database named '$DB_NAME'..."

# Try to find existing DB by name
DB_ID=""

# Prefer JSON output if available
if db_list_json=$(wrangler d1 list --json 2>/dev/null || true); then
    if [ -n "$db_list_json" ]; then
        DB_ID=$(echo "$db_list_json" | python3 -c "import sys,json; objs=json.load(sys.stdin); print(next((o.get('id','') for o in objs if o.get('name','')==sys.argv[1]),''))" "$DB_NAME" || true)
    fi
fi

# Fallback: parse the plain text output for a UUID when JSON is not available
if [ -z "$DB_ID" ]; then
    if list_plain=$(wrangler d1 list 2>/dev/null || true); then
        # Attempt to find a UUID on the same line as the DB name
        DB_ID=$(echo "$list_plain" | grep -F "$DB_NAME" | grep -Eo '[0-9a-fA-F-]{36}' | head -n1 || true)
    fi
fi

if [ -z "$DB_ID" ]; then
    echo "⚙️  Database not found; creating..."
    CREATE_JSON=$(wrangler d1 create "$DB_NAME" --json 2>/dev/null || true)
    if [ -n "$CREATE_JSON" ]; then
        DB_ID=$(echo "$CREATE_JSON" | python3 -c "import sys,json; j=json.load(sys.stdin); print(j.get('id',''))" 2>/dev/null || true)
    fi

    # If create did not return JSON or failed, try listing again and parse
    if [ -z "$DB_ID" ]; then
        if list_plain=$(wrangler d1 list 2>/dev/null || true); then
            DB_ID=$(echo "$list_plain" | grep -F "$DB_NAME" | grep -Eo '[0-9a-fA-F-]{36}' | head -n1 || true)
        fi
    fi
fi

if [ -z "$DB_ID" ]; then
    echo "❌ Failed to create or locate D1 database named '$DB_NAME'."
    echo "   Run 'wrangler d1 list' to inspect available databases." 
    exit 1
fi

echo "✅ Database ID: $DB_ID"

echo
echo "📋 Step 3: Writing .env from .env.example (overwriting if present) and inserting D1_DATABASE_ID..."

TEMPLATE_FILE=".env.example"
TARGET_FILE=".env"
FORCE_OVERWRITE=0

# Support --force to overwrite existing .env
for arg in "${@-}"; do
  if [ "$arg" = "--force" ] || [ "$arg" = "-f" ]; then
    FORCE_OVERWRITE=1
  fi
done

if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "⚠️  .env.example not found, creating a default template at $TEMPLATE_FILE"
    cat > "$TEMPLATE_FILE" <<'EOF'
# Environment variables for BLT-Leaf
# Replace values as needed. This file is used by setup-local.sh to create .env
D1_DATABASE_ID=
GITHUB_TOKEN=
CLOUDFLARE_ACCOUNT_ID=
# Optional: other vars used by your deployment
EOF
fi

# If .env already exists and user did not request overwrite, preserve it and only update/add D1_DATABASE_ID
if [ -f "$TARGET_FILE" ] && [ "$FORCE_OVERWRITE" -ne 1 ]; then
    echo "✅ .env already exists — preserving existing values. Updating only D1_DATABASE_ID."
    if grep -q '^D1_DATABASE_ID=' "$TARGET_FILE"; then
        sed -i.bak -E "s/^D1_DATABASE_ID=.*/D1_DATABASE_ID=$DB_ID/" "$TARGET_FILE" && rm -f "$TARGET_FILE.bak"
    else
        echo "D1_DATABASE_ID=$DB_ID" >> "$TARGET_FILE"
    fi
    echo "✅ Updated $TARGET_FILE"
else
    # Produce .env by replacing or appending D1_DATABASE_ID value
    awk -v dbid="$DB_ID" 'BEGIN{FS=OFS="="; seen=0} /^\s*#/ {print; next} /^\s*$/ {print; next} {key=$1; gsub(/^[ \t]+|[ \t]+$/,"",key); if(key=="D1_DATABASE_ID"){print "D1_DATABASE_ID=" dbid; seen=1} else print $0} END{if(!seen) print "D1_DATABASE_ID=" dbid}' "$TEMPLATE_FILE" > "$TARGET_FILE"
    echo "✅ Wrote $TARGET_FILE (D1_DATABASE_ID set)"
fi

echo
echo "📋 Step 4: Updating wrangler.toml to use D1_DATABASE_ID from environment..."

# Replace the concrete database_id value with an env interpolation
if sed -n '1,200p' wrangler.toml >/dev/null 2>&1; then
    sed -i.bak -E 's/^database_id = .*$/database_id = "${D1_DATABASE_ID}"/' wrangler.toml
    rm -f wrangler.toml.bak
    echo '✅ wrangler.toml updated to use ${D1_DATABASE_ID}'
else
    echo "⚠️  wrangler.toml not found in workspace; please update your wrangler configuration manually."
fi

echo
echo "📋 Step 5: Applying database schema to D1 database (name: $DB_NAME)..."
# Execute schema against the D1 database name
wrangler d1 execute "$DB_NAME" --file=./schema.sql
echo "✅ Schema executed"

echo
echo "🎉 Setup complete!"
echo "👉 Run 'wrangler dev' to start the local development server"
echo "🌐 Open http://localhost:8787 in your browser"
