"""Slack activity per hackathon participant (hackathons with ``trackSlack: true``).

For each participant mapped in the hackathon's ``slackUsersFile`` this counts the messages they
posted in the OWASP and BLT Slack workspaces during the hackathon, with the same search the GSoC
progress tracker uses (blt-gsoc/worker/progress.js): ``search.messages`` with ``from:`` and a date
range, ``count=1``, reading ``messages.total``. Tokens: SLACK_TOKEN_OWASP and SLACK_TOKEN_BLT
(user tokens with ``search:read``). A missing token leaves that workspace out ("—" on the page);
no token at all disables the column. Slack errors never fail the run.

search.messages is Tier 2 (about 20 calls a minute), so calls are spaced by SLACK_CALL_INTERVAL
seconds (default 3.2), a run makes at most SLACK_MAX_CALLS (default 40), and a participant is
re-checked only after SLACK_REFRESH_HOURS (default 20). The counts and check times are kept in the
refresh state (KV), so a run that stops at its budget continues with the oldest checks next time.

Mapping file (YAML, keys are git.owaspblt.org usernames, values a Slack handle for both
workspaces, a per-workspace map, or a Slack member id such as U012ABCDEF):

    slack:
      alice: alice.dev
      bob: {owasp: bob.smith, blt: bob}
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

SERVERS = {"owasp": "SLACK_TOKEN_OWASP", "blt": "SLACK_TOKEN_BLT"}
MEMBER_ID = re.compile(r"^[UW][A-Z0-9]{6,}$")


def load_mapping(path):
    """{lowercase username: {"owasp": handle|None, "blt": handle|None}} from the YAML file."""
    if not path or not os.path.exists(path):
        if path:
            logger.warning("Slack users file not found: %s", path)
        return {}
    try:
        import yaml  # only needed when a hackathon tracks Slack

        with open(path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except Exception as exc:  # a broken file disables Slack, never the run
        logger.error("Could not read Slack users file %s: %s", path, exc)
        return {}
    mapping = {}
    for username, value in ((data.get("slack") if isinstance(data, dict) else None) or {}).items():
        if isinstance(value, str):
            value = {server: value for server in SERVERS}
        if not isinstance(value, dict):
            continue
        handles = {server: str(value[server]).lstrip("@").strip() if value.get(server) else None for server in SERVERS}
        if any(handles.values()):
            mapping[str(username).lower()] = handles
    return mapping


class SlackRateLimited(Exception):
    def __init__(self, retry_after):
        super().__init__(retry_after)
        self.retry_after = retry_after


def search_total(token, handle, after_day, before_day, opener=urlopen):
    """Messages from ``handle`` strictly between the two days (Slack's after:/before: exclude them)."""
    who = f"<@{handle}>" if MEMBER_ID.match(handle) else f"@{handle}"
    query = urlencode({"query": f"from:{who} after:{after_day} before:{before_day}", "count": "1"})
    request = Request(f"https://slack.com/api/search.messages?{query}", headers={
        "Authorization": f"Bearer {token}",
        "User-Agent": "BLT-Hackathons-Stats-Fetcher/2.0",
    })
    try:
        with opener(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 429:
            raise SlackRateLimited(int((exc.headers or {}).get("Retry-After", "30") or 30))
        logger.warning("Slack HTTP %d for %s", exc.code, handle)
        return None
    except (URLError, ValueError, OSError) as exc:
        logger.warning("Slack request failed for %s: %s", handle, exc)
        return None
    if not data.get("ok"):
        if data.get("error") == "ratelimited":
            raise SlackRateLimited(30)
        logger.warning("Slack API error %s for %s", data.get("error"), handle)
        return None
    return int(((data.get("messages") or {}).get("total")) or 0)


def refresh(slug, mapping, start_dt, end_dt, state, env=None, now=None, deadline=None,
            opener=urlopen, sleep=time.sleep):
    """Update ``state`` (this hackathon's Slack section, a dict) and return the stats block."""
    env = os.environ if env is None else env
    now = now or datetime.now(timezone.utc)
    tokens = {server: env.get(var, "") for server, var in SERVERS.items()}
    tokens = {server: token for server, token in tokens.items() if token}
    users = state.setdefault("users", {})
    for username in list(users):
        if username not in mapping:
            del users[username]
    interval = float(env.get("SLACK_CALL_INTERVAL", "3.2"))
    max_calls = int(env.get("SLACK_MAX_CALLS", "40"))
    refresh_after = timedelta(hours=float(env.get("SLACK_REFRESH_HOURS", "20")))
    window_end = min(now, end_dt)
    started = now >= start_dt
    after_day = (start_dt - timedelta(days=1)).date().isoformat()
    before_day = (window_end + timedelta(days=1)).date().isoformat()

    def due(username):
        entry = users.get(username) or {}
        checked = entry.get("checkedAt")
        if not checked:
            return True
        checked_dt = datetime.fromisoformat(checked.replace("Z", "+00:00"))
        if checked_dt >= end_dt:
            return False  # checked after the end: the count is final
        return now > end_dt or now - checked_dt >= refresh_after

    calls = 0
    if tokens and started:
        order = sorted((u for u in mapping if due(u)), key=lambda u: (users.get(u) or {}).get("checkedAt") or "")
        for username in order:
            needed = [s for s in tokens if mapping[username].get(s)]
            if calls + len(needed) > max_calls or (deadline and deadline.remaining() < interval * len(needed) + 5):
                break
            entry = dict(users.get(username) or {})
            try:
                for server in needed:
                    if calls:
                        sleep(interval)
                    calls += 1
                    total = search_total(tokens[server], mapping[username][server], after_day, before_day, opener)
                    if total is not None:
                        entry[server] = total
            except SlackRateLimited as limited:
                logger.warning("Slack rate limit reached (retry after %ss); continuing next run", limited.retry_after)
                break
            entry["checkedAt"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            users[username] = entry
    if calls:
        logger.info("Slack: %d search call(s) for %s", calls, slug)

    servers = [s for s in SERVERS if s in tokens or any(s in u for u in users.values())]
    if not servers:
        return {"enabled": False, "reason": "Slack tokens are not configured"}
    participants = []
    for username in sorted(mapping):
        entry = users.get(username) or {}
        counts = {s: entry.get(s) if started else 0 for s in servers}
        known = [v for v in counts.values() if isinstance(v, int)]
        participants.append({
            "username": username,
            **counts,
            "total": sum(known) if known else None,
            "checkedAt": entry.get("checkedAt"),
        })
    participants.sort(key=lambda p: (-(p["total"] or 0), p["username"]))
    return {
        "enabled": True,
        "servers": servers,
        "totalMessages": sum(p["total"] or 0 for p in participants),
        "participants": participants,
    }


def attach(stats, slack_block):
    """Add ``slackMessages`` to leaderboard entries of mapped participants."""
    stats["slack"] = slack_block
    if not slack_block.get("enabled"):
        return stats
    totals = {p["username"]: p["total"] for p in slack_block["participants"]}
    for board in ("leaderboard", "reviewLeaderboard"):
        for participant in stats.get(board) or []:
            key = str(participant.get("username", "")).lower()
            if key in totals:
                participant["slackMessages"] = totals[key]
    return stats
