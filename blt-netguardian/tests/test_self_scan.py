"""Scheduled self-scan of operator-allowlisted hosts (self_scan.py)."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sys
import types
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

if "workers" not in sys.modules:
    workers_module = types.ModuleType("workers")

    class FakeResponse:
        def __init__(self, body="", status=200, headers=None):
            self.body = body
            self.status = status
            self.headers = dict(headers or {})

    workers_module.Response = FakeResponse
    sys.modules["workers"] = workers_module

from netguardian_db import open_netguardian_db  # noqa: E402
import self_scan  # noqa: E402
from self_scan import (  # noqa: E402
    configured_targets,
    fetch_target,
    run_self_scan,
    validate_target_host,
)
from worker import BLTWorker  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)

BARE_HEADERS = {"Content-Type": "text/html"}  # no hardening headers at all
GOOD_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000",
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


def make_env(targets="owasp.example.org", **extra):
    db = open_netguardian_db(REPO)
    env = SimpleNamespace(
        DB=db,
        NG_DEFAULT_ORG="org-demo",
        AUTHENTICATE_READ_ENDPOINTS="false",
        NG_SELF_SCAN_TARGETS=targets,
        **extra,
    )
    return env, db


class Recorder:
    """Fake fetch returning canned (status, headers, location) per URL."""

    def __init__(self, responses=None, default=(200, BARE_HEADERS, None)):
        self.responses = responses or {}
        self.default = default
        self.calls = []

    async def __call__(self, url):
        self.calls.append(url)
        result = self.responses.get(url, self.default)
        if isinstance(result, Exception):
            raise result
        return result


async def count(db, sql, *params):
    row = await db.prepare(sql).bind(*params).first()
    return row["n"]


# --- target validation (the SSRF boundary) ---------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("owaspblt.org", "owaspblt.org"),
    ("WWW.OWASPBLT.ORG.", "owaspblt.org"),
    ("https://api.owaspblt.org/", "api.owaspblt.org"),
    ("127.0.0.1", None),
    ("10.0.0.5", None),
    ("::1", None),
    ("[::1]", None),
    ("localhost", None),
    ("metadata.google.internal", None),
    ("printer.local", None),
    ("router.home.arpa", None),
    ("site.test", None),
    ("owaspblt.org:8443", None),
    ("user@owaspblt.org", None),
    ("owaspblt.org/admin", None),
    ("http://owaspblt.org", None),
    ("intranet", None),
    ("1.2.3.4.5", None),
    ("-bad-.org", None),
    ("", None),
])
def test_validate_target_host(raw, expected):
    assert validate_target_host(raw) == expected


def test_configured_targets_dedupes_and_drops_invalid():
    env = SimpleNamespace(NG_SELF_SCAN_TARGETS="owaspblt.org, www.owaspblt.org 127.0.0.1\nlocalhost,api.owaspblt.org")
    assert configured_targets(env) == ["owaspblt.org", "api.owaspblt.org"]
    assert configured_targets(SimpleNamespace()) == []


# --- redirects stay on the same host ---------------------------------------

@pytest.mark.asyncio
async def test_redirect_within_host_is_followed():
    fetch = Recorder({
        "https://owaspblt.org/": (301, {}, "https://www.owaspblt.org/"),
        "https://www.owaspblt.org/": (200, GOOD_HEADERS, None),
    })
    url, status, headers = await fetch_target("owaspblt.org", "https://owaspblt.org/", fetch)
    assert (url, status) == ("https://www.owaspblt.org/", 200)
    assert fetch.calls == ["https://owaspblt.org/", "https://www.owaspblt.org/"]


@pytest.mark.asyncio
@pytest.mark.parametrize("location", [
    "https://evil.example.com/",
    "http://owaspblt.org/",
    "https://owaspblt.org:8080/",
    "https://127.0.0.1/",
    "https://user@owaspblt.org.evil.example/",
])
async def test_redirect_off_host_is_not_followed(location):
    fetch = Recorder({"https://owaspblt.org/": (302, {}, location)})
    url, status, _headers = await fetch_target("owaspblt.org", "https://owaspblt.org/", fetch)
    assert (url, status) == ("https://owaspblt.org/", 302)
    assert fetch.calls == ["https://owaspblt.org/"]


@pytest.mark.asyncio
async def test_redirect_loop_is_bounded():
    fetch = Recorder({
        "https://owaspblt.org/": (302, {}, "/a"),
        "https://owaspblt.org/a": (302, {}, "/"),
    })
    with pytest.raises(ValueError):
        await fetch_target("owaspblt.org", "https://owaspblt.org/", fetch)
    assert len(fetch.calls) == self_scan.MAX_REDIRECTS + 1


# --- the scheduled run ------------------------------------------------------

@pytest.mark.asyncio
async def test_disabled_without_targets_touches_nothing():
    env, db = make_env(targets="")
    fetch = Recorder()
    result = await run_self_scan(env=env, db=db, now=NOW, fetch_impl=fetch)
    assert result == {"enabled": False, "scanned": []}
    assert fetch.calls == []
    assert await count(db, "SELECT COUNT(*) AS n FROM domain_jobs") == 0


@pytest.mark.asyncio
async def test_first_run_writes_findings_visible_in_triage():
    env, db = make_env()
    fetch = Recorder()
    result = await run_self_scan(env=env, db=db, now=NOW, fetch_impl=fetch)

    assert fetch.calls == ["https://owasp.example.org/"]
    scanned = result["scanned"][0]
    assert scanned["host"] == "owasp.example.org"
    assert scanned["new_findings"] == scanned["findings"] > 0

    job = await db.prepare("SELECT * FROM domain_jobs").first()
    assert job["status"] == "scanned"
    assert job["source_url"] == self_scan.SOURCE_URL
    assert job["last_scan_at"] == int(NOW.timestamp())
    assert json.loads(job["result_json"])["http_status"] == 200

    # The triage list (anonymous demo read) shows them.
    worker = BLTWorker(env)
    req = SimpleNamespace(url="https://ng.example/api/findings", method="GET", headers={})
    resp = await worker.handle_request(req)
    body = json.loads(resp.body)
    assert resp.status == 200
    assert body["total"] == scanned["findings"]
    rules = {f["rule_id"] for f in body["findings"]}
    assert "http.missing-hsts" in rules
    assert all(f["target"] == "https://owasp.example.org/" for f in body["findings"])


@pytest.mark.asyncio
async def test_rescan_is_skipped_until_interval_and_does_not_duplicate():
    env, db = make_env()
    fetch = Recorder()
    await run_self_scan(env=env, db=db, now=NOW, fetch_impl=fetch)
    first = await count(db, "SELECT COUNT(*) AS n FROM findings")

    # Next cron tick: not due yet, no fetch, no writes.
    result = await run_self_scan(env=env, db=db, now=NOW + timedelta(minutes=5), fetch_impl=fetch)
    assert result["scanned"] == [] and len(fetch.calls) == 1

    # A day later: scanned again, same fingerprints, no new rows.
    result = await run_self_scan(env=env, db=db, now=NOW + timedelta(hours=24), fetch_impl=fetch)
    assert len(fetch.calls) == 2
    assert result["scanned"][0]["new_findings"] == 0
    assert await count(db, "SELECT COUNT(*) AS n FROM findings") == first
    assert await count(db, "SELECT COUNT(*) AS n FROM envelopes") == first


@pytest.mark.asyncio
async def test_per_run_cap_bounds_work():
    env, db = make_env(targets="a.example.org b.example.org c.example.org d.example.org e.example.org")
    fetch = Recorder(default=(200, GOOD_HEADERS, None))
    await run_self_scan(env=env, db=db, now=NOW, fetch_impl=fetch)
    assert len(fetch.calls) == self_scan.DEFAULT_MAX_PER_RUN == 1
    for tick in range(1, 6):
        await run_self_scan(env=env, db=db, now=NOW + timedelta(minutes=5 * tick), fetch_impl=fetch)
    assert len(fetch.calls) == 5  # the sixth tick finds nothing due
    assert sorted(fetch.calls) == [f"https://{h}.example.org/" for h in "abcde"]
    # Hardened hosts: queue rows only, no findings.
    assert await count(db, "SELECT COUNT(*) AS n FROM findings") == 0
    assert await count(db, "SELECT COUNT(*) AS n FROM domain_jobs WHERE status = 'scanned'") == 5


@pytest.mark.asyncio
async def test_max_per_run_is_clamped():
    env, db = make_env(targets=" ".join(f"h{i}.example.org" for i in range(10)), NG_SELF_SCAN_MAX_PER_RUN="999")
    fetch = Recorder(default=(200, GOOD_HEADERS, None))
    await run_self_scan(env=env, db=db, now=NOW, fetch_impl=fetch)
    assert len(fetch.calls) == self_scan.MAX_PER_RUN_CEILING


@pytest.mark.asyncio
async def test_fetch_error_marks_retry_with_backoff():
    env, db = make_env()
    fetch = Recorder({"https://owasp.example.org/": RuntimeError("timeout")})
    result = await run_self_scan(env=env, db=db, now=NOW, fetch_impl=fetch)
    assert "timeout" in result["scanned"][0]["error"]
    job = await db.prepare("SELECT * FROM domain_jobs").first()
    assert job["status"] == "retry_required" and job["claimed_by"] is None

    await run_self_scan(env=env, db=db, now=NOW + timedelta(minutes=5), fetch_impl=fetch)
    assert len(fetch.calls) == 1  # backoff: not retried on the next tick
    await run_self_scan(env=env, db=db, now=NOW + timedelta(hours=1), fetch_impl=fetch)
    assert len(fetch.calls) == 2


@pytest.mark.asyncio
async def test_host_leased_by_a_client_is_left_alone():
    env, db = make_env()
    host = "owasp.example.org"
    await db.prepare(
        "INSERT INTO domain_jobs (id, org_id, host_key, seed_url, status, discovered_at, claimed_by, claim_until)"
        " VALUES ('j1', 'org-demo', ?, ?, 'in_progress', 1, 'scanner-1', ?)"
    ).bind(host, f"https://{host}/", int(NOW.timestamp()) + 60).run()
    fetch = Recorder()
    result = await run_self_scan(env=env, db=db, now=NOW, fetch_impl=fetch)
    assert result["scanned"] == [] and fetch.calls == []


@pytest.mark.asyncio
async def test_queue_hosts_not_on_allowlist_are_never_fetched():
    env, db = make_env(targets="owasp.example.org")
    await db.prepare(
        "INSERT INTO domain_jobs (id, org_id, host_key, seed_url, status, discovered_at)"
        " VALUES ('j2', 'org-demo', 'third-party.example.com', 'https://third-party.example.com/', 'pending', 1)"
    ).run()
    fetch = Recorder()
    await run_self_scan(env=env, db=db, now=NOW, fetch_impl=fetch)
    assert fetch.calls == ["https://owasp.example.org/"]


@pytest.mark.asyncio
async def test_handle_scheduled_runs_every_step_and_survives_scan_errors(monkeypatch):
    env, db = make_env()

    async def boom(**_kwargs):
        raise RuntimeError("scan blew up")

    monkeypatch.setattr("worker.run_self_scan", boom)
    summary = await BLTWorker(env).handle_scheduled()
    assert "self_scan" not in summary
    assert summary["leases_expired"] == 0
    assert summary["webhooks"] == 0


@pytest.mark.asyncio
async def test_discovery_status_reports_real_queue_state():
    env, db = make_env()
    await run_self_scan(env=env, db=db, now=datetime.now(timezone.utc), fetch_impl=Recorder())
    worker = BLTWorker(env)
    req = SimpleNamespace(url="https://ng.example/api/discovery/status", method="GET", headers={})
    resp = await worker.handle_request(req)
    body = json.loads(resp.body)
    assert resp.status == 200, body
    assert body["current_target"] is None
    assert body["status"] == "idle"
    assert body["scanned_today"] == 1
    assert body["self_scan_targets"] == 1
    assert body["stats"]["domains_discovered"] == 1
    assert body["vulnerabilities_found"] > 0

    req = SimpleNamespace(url="https://ng.example/api/discovery/recent?limit=5", method="GET", headers={})
    recent = json.loads((await worker.handle_request(req)).body)
    assert [d["target"] for d in recent["discoveries"]] == ["owasp.example.org"]
    assert recent["discoveries"][0]["source"] == "self_scan"
    assert "example.com" not in json.dumps(body)
