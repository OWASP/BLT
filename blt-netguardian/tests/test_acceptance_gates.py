"""W7 acceptance gates: replay golden fixtures through process_ingest."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone

import pytest

from acceptance_fixtures import CASES_PATH, REPO_ROOT, build_env, run_case
from netguardian_db import open_netguardian_db


@pytest.fixture(scope="module")
def pack():
    return json.loads(CASES_PATH.read_text())


@pytest.fixture(scope="module")
def secret(pack):
    return bytes.fromhex(pack["meta"]["secret_hex"])


@pytest.fixture(scope="module")
def payload_key(pack):
    return base64.b64decode(pack["meta"]["payload_key_b64"])


@pytest.fixture
def env(pack):
    return build_env(pack)


@pytest.fixture
def db():
    database = open_netguardian_db(REPO_ROOT)
    yield database
    database.conn.close()


def _now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_each_acceptance_case(pack, env, db, secret, payload_key):
    now = _now()
    failures = []
    for case in pack["cases"]:
        outcome = await run_case(
            pack, case, env=env, db=db, secret=secret, payload_key=payload_key, now=now,
        )
        if not outcome["ok"]:
            failures.append(outcome)
    assert not failures, f"fixture failures: {json.dumps(failures, indent=2)}"


@pytest.mark.asyncio
async def test_accept_success_gate_threshold(pack, env, secret, payload_key):
    """≥95% of accept fixtures must hit expected status (W7 gate)."""
    threshold = float(pack["meta"]["accept_success_threshold"])
    accept_cases = [c for c in pack["cases"] if c["kind"] == "accept"]
    assert accept_cases, "no accept cases in fixture pack"

    database = open_netguardian_db(REPO_ROOT)
    try:
        now = _now()
        results = []
        for case in accept_cases:
            outcome = await run_case(
                pack,
                case,
                env=env,
                db=database,
                secret=secret,
                payload_key=payload_key,
                now=now,
            )
            results.append(outcome)
    finally:
        database.conn.close()

    passed = sum(1 for r in results if r["ok"])
    rate = passed / len(results)
    assert rate >= threshold, (
        f"accept success {rate:.0%} < {threshold:.0%}: "
        f"{json.dumps(results, indent=2)}"
    )


@pytest.mark.asyncio
async def test_reject_cases_all_correct(pack, env, secret, payload_key):
    reject_cases = [c for c in pack["cases"] if c["kind"] == "reject"]
    database = open_netguardian_db(REPO_ROOT)
    try:
        now = _now()
        for case in reject_cases:
            outcome = await run_case(
                pack,
                case,
                env=env,
                db=database,
                secret=secret,
                payload_key=payload_key,
                now=now,
            )
            assert outcome["ok"], f"reject case failed: {outcome}"
    finally:
        database.conn.close()
