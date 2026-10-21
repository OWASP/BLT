"""public/monitors.json: valid ids, unique, and the shape check_monitor reads."""

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
MONITORS = json.loads((ROOT / "public" / "monitors.json").read_text())


def test_monitor_ids_are_valid_and_unique():
    ids = [m["id"] for m in MONITORS]
    assert len(ids) == len(set(ids))
    for monitor in MONITORS:
        assert re.fullmatch(r"[a-z0-9_-]+", monitor["id"])
        assert monitor["url"].startswith("https://")
        assert isinstance(monitor.get("keyword", ""), str)
        assert isinstance(monitor.get("enabled", True), bool)


def test_owasp_welcome_monitor():
    """Lettuce's /health/welcome answers 503 when the OWASP welcome is failing and only says
    welcome-healthy when it works. The check is off until the cut-over turns the welcome on."""
    monitor = next(m for m in MONITORS if m["id"] == "lettuce_owasp_welcome")
    assert monitor["url"] == "https://lettuce.owaspblt.org/health/welcome"
    assert monitor["keyword"] == "welcome-healthy"


def test_forge_monitor_reads_git_data():
    """The forge check reads repository stats, which need the git backend, so it fails when the
    web app is up but its git gateway is not (HTTP 503 mirror_unavailable)."""
    monitor = next(m for m in MONITORS if m["id"] == "git_owaspblt")
    assert monitor["url"] == "https://git.owaspblt.org/api/repo/owasp-blt/BLT/stats"
    assert monitor["keyword"] == "commitCount"
    assert monitor["enabled"] is True
