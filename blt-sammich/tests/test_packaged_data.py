"""The data files reach the deployed Worker.

Wrangler bundles src/ as Python modules plus text modules chosen by file type; .md and .json
only go in because of the [[rules]] in wrangler.toml. These tests rebuild that bundle (only
the files Wrangler would take) in a temp dir and load the worker from it, so data that the
deploy would drop shows up as the one-line fallback welcome or empty /project and /repo.
"""

import fnmatch
import json
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
# Text and Python types Wrangler bundles by default for Python Workers (seen in a dry run).
DEFAULT_GLOBS = ["**/*.py", "**/*.txt", "**/*.html"]


def rule_globs():
    config = tomllib.loads((ROOT / "wrangler.toml").read_text())
    globs = []
    for rule in config.get("rules", []):
        globs.extend(rule.get("globs", []))
    return globs


def bundled(rel_path, globs):
    # Wrangler globs are relative to src/; "**/" also matches files at the top level.
    return any(
        fnmatch.fnmatch(rel_path, g) or (g.startswith("**/") and fnmatch.fnmatch(rel_path, g[3:]))
        for g in globs
    )


def test_every_data_file_is_covered_by_a_module_rule():
    globs = rule_globs() + DEFAULT_GLOBS
    files = [p for p in (SRC / "data").rglob("*") if p.is_file()]
    assert files
    missed = [str(p.relative_to(SRC)) for p in files if not bundled(str(p.relative_to(SRC)), globs)]
    assert not missed, "not bundled into the Worker: {0}".format(missed)


def test_welcome_projects_and_repos_load_from_the_bundle(tmp_path):
    globs = rule_globs() + DEFAULT_GLOBS
    bundle = tmp_path / "bundle"
    for path in SRC.rglob("*"):
        rel = str(path.relative_to(SRC))
        if path.is_file() and "__pycache__" not in rel and bundled(rel, globs):
            (bundle / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, bundle / rel)
    assert not (bundle.parent / "data").exists()  # nothing outside src/ to fall back on

    probe = (
        "import json, worker\n"
        "print(json.dumps({\n"
        "  'welcome': worker.get_workspace_welcome_message('T04T40NHX'),\n"
        "  'default_welcome': worker.get_workspace_welcome_message('TNOTEAM'),\n"
        "  'channel_join': worker.get_channel_join_message('T070JPE5BQQ', 'C06V9S85YR1'),\n"
        "  'projects': len(worker.PROJECT_DATA),\n"
        "  'repos': len(worker.REPO_DATA),\n"
        "}))\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", probe], cwd=bundle, capture_output=True, text=True, check=True
    )
    loaded = json.loads(out.stdout.strip().splitlines()[-1])

    welcome = (SRC / "data" / "message-T04T40NHX-team_join.md").read_text().strip()
    assert loaded["welcome"] == welcome
    assert loaded["default_welcome"] == (SRC / "data" / "welcome_message.md").read_text().strip()
    assert loaded["channel_join"]
    assert loaded["projects"] == len(json.loads((SRC / "data" / "projects.json").read_text())) > 0
    assert loaded["repos"] == len(json.loads((SRC / "data" / "repos.json").read_text())) > 0
