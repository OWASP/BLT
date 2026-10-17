#!/usr/bin/env python3
"""Apply Cloudflare D1 migrations before deploy.

This script reads the first D1 database entry from wrangler.toml unless
D1_DATABASE_NAME is provided in the environment.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    import tomli as tomllib  # type: ignore


def load_database_name(wrangler_toml: Path) -> str:
    env_name = os.getenv("D1_DATABASE_NAME", "").strip()
    if env_name:
        return env_name

    if not wrangler_toml.exists():
        raise RuntimeError(f"wrangler config not found: {wrangler_toml}")

    with wrangler_toml.open("rb") as f:
        config = tomllib.load(f)

    d1_dbs = config.get("d1_databases") or []
    if not d1_dbs:
        raise RuntimeError("No [[d1_databases]] entries found in wrangler.toml")

    db_name = str((d1_dbs[0] or {}).get("database_name") or "").strip()
    if not db_name:
        raise RuntimeError("Missing database_name in first [[d1_databases]] entry")
    return db_name


def main() -> int:
    if os.getenv("SKIP_D1_MIGRATIONS", "").strip() == "1":
        print("[migrate] SKIP_D1_MIGRATIONS=1 set, skipping migrations")
        return 0

    if shutil.which("wrangler") is None:
        print("[migrate] wrangler CLI not found in PATH", file=sys.stderr)
        return 1

    repo_root = Path(__file__).resolve().parents[1]
    wrangler_toml = repo_root / "wrangler.toml"

    try:
        db_name = load_database_name(wrangler_toml)
    except Exception as e:
        print(f"[migrate] {e}", file=sys.stderr)
        return 1

    cmd = ["wrangler", "d1", "migrations", "apply", db_name, "--remote"]
    print("[migrate] running:", " ".join(cmd))

    proc = subprocess.run(cmd, cwd=str(repo_root), check=False)
    if proc.returncode != 0:
        print(f"[migrate] migration command failed with code {proc.returncode}")
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
