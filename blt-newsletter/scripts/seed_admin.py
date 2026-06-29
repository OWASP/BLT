#!/usr/bin/env python3
import argparse
import os
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.admin_auth import hash_password
from src.newsletter_validation import email_hash
from src.newsletter_validation import normalize_email


DEFAULT_EMAIL_HASH_SECRET = "development-email-hash-secret"


def sql_quote(value):
    if value is None:
        return "NULL"

    return "'" + str(value).replace("'", "''") + "'"


def build_insert_sql(email, password, name=None, secret=None):
    normalized_email = normalize_email(email)
    if not normalized_email:
        raise ValueError("email is required")

    admin_id = "adm_" + uuid.uuid4().hex
    secret_value = secret or os.environ.get("EMAIL_HASH_SECRET") or DEFAULT_EMAIL_HASH_SECRET
    values = [
        admin_id,
        normalized_email,
        email_hash(normalized_email, secret_value),
        name or "",
        "admin",
        hash_password(password),
        "active",
        "{}",
    ]

    return (
        "INSERT INTO newsletter_admins "
        "(id, email, email_hash, name, role, password_hash, status, metadata_json) "
        "VALUES ("
        + ", ".join(sql_quote(value) for value in values)
        + ");"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Print SQL for seeding a local BLT Newsletter admin. Pipe the output "
            "to wrangler d1 execute; this script does not connect to D1."
        ),
        epilog=(
            "Example: EMAIL_HASH_SECRET=dev-secret python3 scripts/seed_admin.py "
            "--email admin@example.com --password 'change-me' --name 'Site Admin'"
        ),
    )
    parser.add_argument("--email", required=True, help="Admin email address.")
    parser.add_argument("--password", required=True, help="Admin password to hash.")
    parser.add_argument("--name", default="", help="Optional display name.")
    parser.add_argument(
        "--email-hash-secret",
        default=None,
        help="Optional HMAC secret. Defaults to EMAIL_HASH_SECRET or the local dev fallback.",
    )
    args = parser.parse_args(argv)
    if len(args.password) < 8:
        print("Admin password must be at least 8 characters.", file=sys.stderr)
        return 2

    print(
        build_insert_sql(
            args.email,
            args.password,
            name=args.name,
            secret=args.email_hash_secret,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
