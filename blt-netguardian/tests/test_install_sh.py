"""Guards for the no-signup install.sh one-liner."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts" / "install.sh").read_text()


def test_install_sh_requires_https_target_and_local_detect_export():
    assert "detect_export.py" in SCRIPT
    assert "/api/detect/headers" not in SCRIPT
    assert "sh -s --" in SCRIPT
    assert "--secret-hex" in SCRIPT


def test_install_sh_usage_without_url(tmp_path, monkeypatch):
    import subprocess

    result = subprocess.run(
        ["sh", str(ROOT / "scripts" / "install.sh")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "your-site.example" in result.stderr


def test_install_sh_rejects_non_url():
    import subprocess

    result = subprocess.run(
        ["sh", str(ROOT / "scripts" / "install.sh"), "not-a-url"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "http(s)" in result.stderr
