"""public/ is the [assets] directory, so everything in it is served to the internet."""

import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"


def test_assets_directory_is_public_folder():
    config = tomllib.loads((ROOT / "wrangler.toml").read_text())
    assets = config["assets"]
    assert assets["directory"] == "public"
    # Wrangler ignores "include"; its presence would suggest a filter that doesn't exist.
    assert "include" not in assets


def test_assets_directory_has_no_code_config_or_secrets():
    bad = []
    for path in PUBLIC.rglob("*"):
        name = path.name.lower()
        if (
            path.suffix in (".py", ".pyc", ".toml")
            or name.startswith(".env")
            or name.startswith(".dev.vars")
            or "local_settings" in name
            or name == "__pycache__"
        ):
            bad.append(str(path.relative_to(ROOT)))
    assert not bad, "served publicly from public/: {0}".format(bad)


def test_assets_the_worker_reads_are_in_public():
    worker = (ROOT / "src" / "worker.py").read_text()
    welcome = (ROOT / "src" / "lettuce" / "welcome_bot.py").read_text()
    # Channel-join templates are fetched from env.ASSETS as data/<file>.
    assert 'f"data/{filename}"' in worker
    assert list((PUBLIC / "data").glob("message-*-ephemeral.md"))
    for logo in re.findall(r"/docs/static/[\w.-]+\.png", worker + welcome):
        assert (PUBLIC / logo.lstrip("/")).is_file(), logo
