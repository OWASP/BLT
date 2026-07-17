#!/usr/bin/env python3
"""Print a one-screen summary of W7 acceptance gates."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from test_acceptance_gates import CASES_PATH, run_case  # noqa: E402
from netguardian_db import open_netguardian_db  # noqa: E402
import base64  # noqa: E402
from datetime import datetime, timezone  # noqa: E402


async def main() -> int:
    pack = json.loads(CASES_PATH.read_text())
    meta = pack["meta"]
    secret = bytes.fromhex(meta["secret_hex"])
    payload_key = base64.b64decode(meta["payload_key_b64"])
    env = SimpleNamespace(
        NG_SENDER_SECRETS=json.dumps({
            f"{meta['org_id']}:{meta['sender_id']}:{meta['kid']}": meta["secret_hex"],
        }),
        NG_ORG_API_TOKENS=json.dumps({"triage-token": meta["org_id"]}),
        NG_PAYLOAD_KEYS=json.dumps({meta["org_id"]: meta["payload_key_b64"]}),
        NG_INGEST_RPM="120",
        NG_INGEST_MAX_BODY_BYTES=str(1_048_576),
    )
    db = open_netguardian_db(ROOT)
    now = datetime.now(timezone.utc)
    rows = []
    try:
        for case in pack["cases"]:
            rows.append(
                await run_case(
                    pack,
                    case,
                    env=env,
                    db=db,
                    secret=secret,
                    payload_key=payload_key,
                    now=now,
                )
            )
    finally:
        db.conn.close()

    accept = [r for r in rows if r["kind"] == "accept"]
    reject = [r for r in rows if r["kind"] == "reject"]
    accept_ok = sum(1 for r in accept if r["ok"])
    reject_ok = sum(1 for r in reject if r["ok"])
    rate = accept_ok / len(accept) if accept else 0.0
    threshold = float(meta["accept_success_threshold"])

    print("NetGuardian W7 acceptance gates")
    print(f"  accept: {accept_ok}/{len(accept)} ({rate:.0%})  threshold ≥ {threshold:.0%}")
    print(f"  reject: {reject_ok}/{len(reject)} (must be 100%)")
    for r in rows:
        mark = "PASS" if r["ok"] else "FAIL"
        print(f"  [{mark}] {r['id']:24} status={r['status']} error={r['error']}")

    if rate < threshold or reject_ok != len(reject):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
