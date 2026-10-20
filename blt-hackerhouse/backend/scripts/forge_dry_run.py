"""Print the events the forge poller would create, without writing anywhere.

Anonymous GETs against git.owaspblt.org only; no D1, no queue.

Usage (from blt-hackerhouse/):
    python backend/scripts/forge_dry_run.py            # a first run: the backfill window
    python backend/scripts/forge_dry_run.py --json     # the events as JSON lines
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingestion.forge_poller import ForgeClient, ForgeConfig, poll  # noqa: E402


def _get(url: str):
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "BLT-Hackerhouse-dry-run/1.0"})
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return exc.code, None


async def get_json(url: str):
    return await asyncio.to_thread(_get, url)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="print each event as a JSON line")
    args = parser.parse_args()
    config = ForgeConfig.from_env(None)
    client = ForgeClient(get_json, config)
    result = await poll(client, None, config)
    for event in result.events:
        if args.json:
            print(json.dumps(event.model_dump(mode="json")))
        else:
            print(f"{event.timestamp:%Y-%m-%d %H:%M}Z  {event.event_type:<14} {event.actor_name[:20]:<20} "
                  f"{event.repository[:18]:<18} {str(event.metadata.get('title') or '')[:60]}")
    state = dict(result.state)
    summary = {
        "events": len(result.events),
        "skipped_bots": result.skipped_bots,
        "requests": result.requests,
        "complete": result.complete,
        "cursor_bytes": len(json.dumps(state, separators=(",", ":"))),
        "cursor": {k: v for k, v in state.items() if k not in ("folders", "issues", "pulls")},
    }
    print(json.dumps(summary, indent=1), file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
