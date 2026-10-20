"""The leaderboard page escapes author names, and its inline script parses."""

import pathlib
import re
import shutil
import subprocess

import pytest

UI = pathlib.Path(__file__).resolve().parents[2] / "UI"


def test_leaderboard_escapes_display_names():
    page = (UI / "leaderboard.html").read_text()
    assert "+ entry.display_name +" not in page
    assert "esc(entry.display_name)" in page
    assert "safeUrl(entry.avatar_url)" in page


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_leaderboard_inline_script_is_valid_javascript(tmp_path):
    page = (UI / "leaderboard.html").read_text()
    scripts = re.findall(r"<script(?![^>]*src)[^>]*>([\s\S]*?)</script>", page)
    js = tmp_path / "leaderboard.js"
    js.write_text("\n;\n".join(scripts))
    result = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
