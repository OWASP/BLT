"""
Optional maintainer CLI.
Requires you to use 'wrangler d1 execute' under the hood (simple + no extra APIs).
"""

import argparse
import json
import subprocess
import shlex
import sys
import pathlib

def run(cmd):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if p.returncode != 0:
        print(p.stderr)
        sys.exit(p.returncode)
    return p.stdout

def esc(v):
    """Escape single quotes for safe SQL string interpolation."""
    return v.replace("'", "''")

def add_domain(args):
    pub = pathlib.Path(args.public_key).read_text(encoding="utf-8").strip()
    # Validate JSON
    jwk = json.loads(pub)
    if jwk.get("kty") != "EC" or jwk.get("crv") != "P-256":
        raise SystemExit("public_key must be EC P-256 JWK")

    sql = f"""
INSERT INTO domains (domain, org_email, alg, key_id, public_key_jwk, is_active)
VALUES ('{esc(args.domain)}', '{esc(args.email)}', 'ECDH_P256_HKDF_SHA256_AESGCM', '{esc(args.key_id)}', '{esc(pub)}', 1)
ON CONFLICT(domain) DO UPDATE SET
  org_email=excluded.org_email,
  alg=excluded.alg,
  key_id=excluded.key_id,
  public_key_jwk=excluded.public_key_jwk,
  is_active=excluded.is_active,
  updated_at=(strftime('%Y-%m-%dT%H:%M:%fZ','now'));
"""
    cmd = f"wrangler d1 execute {shlex.quote(args.db)} --command {shlex.quote(sql)}"
    print(run(cmd))
    print("✅ Upserted domain in D1")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="blt_zero")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("add-domain")
    s.add_argument("--domain", required=True)
    s.add_argument("--email", required=True)
    s.add_argument("--key-id", required=True)
    s.add_argument("--public-key", required=True)
    s.set_defaults(func=add_domain)

    args = ap.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()