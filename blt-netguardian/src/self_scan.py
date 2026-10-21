"""Scheduled header scan of hosts the operator owns (``NG_SELF_SCAN_TARGETS``).

Third-party scanning stays on the user-run client: the Worker never scans a
host because someone submitted it. The only hosts this module fetches are the
ones listed in ``NG_SELF_SCAN_TARGETS``, a deploy-time variable the operator
controls; listing a host there is the operator's consent to scan it. Empty or
unset means the feature is off.

Each cron run:

* reads the listed hosts' rows from ``domain_jobs`` (one indexed SELECT),
* scans at most ``NG_SELF_SCAN_MAX_PER_RUN`` hosts that are due (default 1,
  at most 3; a host is due once per ``NG_SELF_SCAN_INTERVAL_HOURS``, default
  24). At one host per 5-minute run that still covers 288 hosts a day.
* makes one GET to ``https://<host>/`` (redirects followed only within the
  same host, at most 2 hops, 5 s timeout each) and runs the HTTP header rules.
  The worst case per host is 15 s, so a run stays inside the dispatcher's
  30-second scheduled-event budget even after a Python cold start.
* writes a finding only for a fingerprint the org does not have yet, so
  re-scanning an unchanged host writes just the queue row.

The fetch never leaves the allowlist: hostnames only (no IP literals, ports,
userinfo or internal suffixes), https only, no cross-host redirects.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Mapping, Optional
from urllib.parse import urljoin, urlparse

from auth import default_org_id
from d1_compat import d1_rows, row_get
from detect.http_headers import scan_headers
from domain_normalize import strip_www
from domain_queue_store import DomainQueueStore
from findings_store import FindingsStore
from ingest_store import IngestStore
from js_fetch import fetch_init

SENDER_ID = "netguardian-cron"
KID = "self-scan"
SOURCE_URL = "netguardian:self-scan-allowlist"

DEFAULT_MAX_PER_RUN = 1
MAX_PER_RUN_CEILING = 3
DEFAULT_INTERVAL_HOURS = 24
RETRY_BACKOFF_SECONDS = 3600
LEASE_SECONDS = 120
MAX_TARGETS = 25
MAX_REDIRECTS = 2
FETCH_TIMEOUT_MS = 5_000
MAX_FINDINGS_PER_TARGET = 20
USER_AGENT = "blt-netguardian-selfscan (+https://netguardian.owaspblt.org/)"

_HOST_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_INTERNAL_SUFFIXES = (
    ".local", ".localhost", ".internal", ".intranet", ".lan", ".home",
    ".corp", ".private", ".home.arpa", ".test", ".invalid", ".example",
    ".onion",
)

FetchFn = Callable[[str], Awaitable[tuple[int, dict[str, str], Optional[str]]]]


def validate_target_host(raw: str) -> Optional[str]:
    """Return a lowercase public hostname, or None when it is not scannable.

    Accepts a bare hostname (``www.`` is folded into the apex, matching the
    domain queue's host_key). Rejects IP literals, ports, paths, userinfo,
    single-label names and reserved/internal suffixes.
    """
    text = str(raw or "").strip().lower().rstrip(".")
    if text.startswith("https://"):
        text = text[len("https://"):].rstrip("/")
    if not text or len(text) > 253:
        return None
    if any(ch in text for ch in "/:@?#[]\\ \t"):
        return None
    try:
        ipaddress.ip_address(text)
        return None
    except ValueError:
        pass
    labels = text.split(".")
    if len(labels) < 2 or not all(_HOST_LABEL.match(label) for label in labels):
        return None
    if labels[-1].isdigit():
        return None
    if text == "localhost" or any(text.endswith(suffix) for suffix in _INTERNAL_SUFFIXES):
        return None
    return strip_www(text)


def configured_targets(env: Any) -> list[str]:
    """Validated, de-duplicated hosts from ``NG_SELF_SCAN_TARGETS`` (comma/space list)."""
    raw = str(getattr(env, "NG_SELF_SCAN_TARGETS", "") or "")
    hosts: list[str] = []
    for item in re.split(r"[\s,]+", raw):
        host = validate_target_host(item) if item else None
        if host and host not in hosts:
            hosts.append(host)
    return hosts[:MAX_TARGETS]


def _env_int(env: Any, key: str, default: int, lo: int, hi: int) -> int:
    try:
        value = int(str(getattr(env, key, "") or default))
    except ValueError:
        value = default
    return max(lo, min(hi, value))


def self_scan_org(env: Any) -> str:
    raw = str(getattr(env, "NG_SELF_SCAN_ORG", "") or "").strip()
    return raw or default_org_id(env)


def _job_id(org_id: str, host_key: str) -> str:
    # Same id scheme as the domain queue, so a host submitted by a client and
    # the same host on the allowlist share one row.
    return hashlib.sha256(f"{org_id}:{host_key}".encode()).hexdigest()[:16]


def is_due(job: Mapping[str, Any], now: int, interval_seconds: int) -> bool:
    status = job.get("status")
    last = int(job.get("last_scan_at") or 0)
    if status == "pending":
        return True
    if status == "in_progress":
        until = job.get("claim_until")
        return until is None or int(until) < now
    if status == "retry_required":
        return now - last >= RETRY_BACKOFF_SECONDS
    return now - last >= interval_seconds  # scanned / failed


def _same_site(host_key: str, url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.port not in (None, 443) or parsed.username:
        return False
    return strip_www((parsed.hostname or "").lower().rstrip(".")) == host_key


async def _default_fetch(url: str) -> tuple[int, dict[str, str], Optional[str]]:
    """One GET without following redirects; returns (status, headers, location)."""
    from js import AbortSignal, fetch  # type: ignore[import-not-found]

    resp = await fetch(url, fetch_init({
        "method": "GET",
        "redirect": "manual",
        "headers": {"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.5"},
        "signal": AbortSignal.timeout(FETCH_TIMEOUT_MS),
    }))
    headers: dict[str, str] = {}
    for entry in resp.headers.entries():
        headers[str(entry[0])] = str(entry[1])
    get_set_cookie = getattr(resp.headers, "getSetCookie", None)
    if callable(get_set_cookie):
        cookies = [str(c) for c in get_set_cookie()]
        if cookies:
            headers["set-cookie"] = "\n".join(cookies)
    location = resp.headers.get("Location")
    try:
        if resp.body:
            await resp.body.cancel()
    except Exception:  # noqa: BLE001 - body already consumed or not cancellable
        pass
    return int(resp.status), headers, (str(location) if location else None)


async def fetch_target(host_key: str, seed_url: str, fetch: FetchFn) -> tuple[str, int, dict[str, str]]:
    """GET ``seed_url``, following redirects only within the same host."""
    url = seed_url
    for _ in range(MAX_REDIRECTS + 1):
        if not _same_site(host_key, url):
            raise ValueError(f"refusing off-site URL {url[:200]}")
        status, headers, location = await fetch(url)
        if status in (301, 302, 303, 307, 308) and location:
            nxt = urljoin(url, location)
            if not _same_site(host_key, nxt):
                # Stop here; evaluate the redirect response itself.
                return url, status, headers
            url = nxt
            continue
        return url, status, headers
    raise ValueError("too many redirects")


async def _claim(db: Any, org_id: str, job: Mapping[str, Any], now: int) -> bool:
    """Optimistic claim: only succeeds if the row is unchanged since we read it."""
    await db.prepare(
        """
        UPDATE domain_jobs
        SET status = 'in_progress', claimed_by = ?, claim_until = ?
        WHERE org_id = ? AND id = ? AND status = ?
          AND COALESCE(last_scan_at, 0) = ? AND COALESCE(claim_until, 0) = ?
        """
    ).bind(
        SENDER_ID, now + LEASE_SECONDS, org_id, job["id"], job["status"],
        int(job.get("last_scan_at") or 0), int(job.get("claim_until") or 0),
    ).run()
    row = await DomainQueueStore(db).get_by_id(org_id, job["id"])
    return bool(row and row.get("claimed_by") == SENDER_ID
                and int(row.get("claim_until") or 0) == now + LEASE_SECONDS)


async def _store_findings(db: Any, org_id: str, payloads: list[dict], now: int) -> int:
    """Insert findings whose fingerprint is new for the org; return how many."""
    findings = FindingsStore(db)
    ingest = IngestStore(db)
    created = 0
    for payload in payloads[:MAX_FINDINGS_PER_TARGET]:
        fingerprint = str(payload.get("fingerprint") or "")
        if not fingerprint or await findings.find_by_fingerprint(org_id, fingerprint):
            continue
        payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        digest = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        seed = f"{org_id}:{fingerprint}"
        try:
            await ingest.insert_accepted(
                envelope_id=hashlib.sha256(f"env-{seed}".encode()).hexdigest()[:16],
                finding_id=hashlib.sha256(f"fnd-{seed}".encode()).hexdigest()[:16],
                org_id=org_id,
                sender_id=SENDER_ID,
                kid=KID,
                nonce=f"selfscan-{fingerprint}",
                body_digest=digest,
                payload_digest=digest,
                issued_at_unix=now,
                received_at_unix=now,
                payload_json=payload_json,
                payload=payload,
            )
        except Exception as exc:  # noqa: BLE001 - one bad row must not stop the run
            print(f"[self-scan] could not store {fingerprint}: {type(exc).__name__}: {exc}")
            continue
        created += 1
    return created


async def run_self_scan(
    *,
    env: Any,
    db: Any,
    now: Optional[datetime] = None,
    fetch_impl: Optional[FetchFn] = None,
) -> dict[str, Any]:
    """Scan due allowlisted hosts; bounded per run. Never raises for a bad target."""
    hosts = configured_targets(env)
    if db is None or not hosts:
        return {"enabled": False, "scanned": []}

    ts = int((now or datetime.now(timezone.utc)).timestamp())
    org_id = self_scan_org(env)
    max_per_run = _env_int(env, "NG_SELF_SCAN_MAX_PER_RUN", DEFAULT_MAX_PER_RUN, 1, MAX_PER_RUN_CEILING)
    interval = 3600 * _env_int(env, "NG_SELF_SCAN_INTERVAL_HOURS", DEFAULT_INTERVAL_HOURS, 1, 24 * 30)
    fetch = fetch_impl or _default_fetch

    placeholders = ", ".join("?" for _ in hosts)
    rows = d1_rows(await db.prepare(
        f"""
        SELECT id, host_key, seed_url, status, last_scan_at, claim_until
        FROM domain_jobs WHERE org_id = ? AND host_key IN ({placeholders})
        """
    ).bind(org_id, *hosts).all())
    jobs = {str(row_get(r, "host_key")): {
        "id": row_get(r, "id"),
        "host_key": row_get(r, "host_key"),
        "seed_url": row_get(r, "seed_url"),
        "status": row_get(r, "status"),
        "last_scan_at": row_get(r, "last_scan_at"),
        "claim_until": row_get(r, "claim_until"),
    } for r in rows}

    due: list[dict] = []
    for host in hosts:
        job = jobs.get(host)
        if job is None:
            job = {"id": _job_id(org_id, host), "host_key": host, "seed_url": f"https://{host}/",
                   "status": "pending", "last_scan_at": None, "claim_until": None, "new": True}
        if is_due(job, ts, interval):
            due.append(job)
    due.sort(key=lambda j: int(j.get("last_scan_at") or 0))

    store = DomainQueueStore(db)
    results: list[dict] = []
    for job in due[:max_per_run]:
        host = job["host_key"]
        if job.get("new"):
            await store.insert_pending(
                job_id=job["id"], org_id=org_id, host_key=host, seed_url=job["seed_url"],
                discovered_at=ts, source_url=SOURCE_URL,
            )
        if not await _claim(db, org_id, job, ts):
            results.append({"host": host, "skipped": "claimed elsewhere"})
            continue
        try:
            final_url, status, headers = await fetch_target(host, f"https://{host}/", fetch)
        except Exception as exc:  # noqa: BLE001 - network errors become a retry
            error = f"{type(exc).__name__}: {exc}"[:300]
            await store.fail(org_id=org_id, job_id=job["id"], sender_id=SENDER_ID, now=ts, error=error)
            results.append({"host": host, "error": error})
            continue
        payloads = [f.to_payload() for f in scan_headers(final_url, headers, status=status)]
        created = await _store_findings(db, org_id, payloads, ts)
        summary = {
            "source": "self-scan",
            "url": final_url,
            "http_status": status,
            "findings": len(payloads),
            "new_findings": created,
            "rules": sorted({p["rule_id"] for p in payloads}),
        }
        await store.complete(
            org_id=org_id, job_id=job["id"], sender_id=SENDER_ID, now=ts,
            result_json=json.dumps(summary, separators=(",", ":")),
        )
        results.append({"host": host, **summary})
    return {"enabled": True, "org_id": org_id, "due": len(due), "scanned": results}
