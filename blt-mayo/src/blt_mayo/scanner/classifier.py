from __future__ import annotations

from pathlib import Path

from blt_mayo.models.artifact import FileMetadata
from blt_mayo.models.enums import ArtifactType, PathSensitivity

STARTUP_NAMES = {
    ".bashrc",
    ".bash_profile",
    ".bash_login",
    ".profile",
    ".zshrc",
    ".zprofile",
    "profile",
    "rc.local",
}
SYSTEMD_SUFFIXES = {".service", ".timer", ".socket", ".path", ".mount"}
CONFIG_SUFFIXES = {".conf", ".cfg", ".ini", ".yaml", ".yml", ".toml"}


def classify_sensitivity(path: Path) -> PathSensitivity:
    text = path.as_posix()
    parts = set(path.parts)
    if text.startswith(
        ("/etc/", "/root/", "/var/spool/cron/", "/usr/lib/systemd/", "/lib/systemd/")
    ):
        return PathSensitivity.CRITICAL
    if any(marker in text for marker in ("/cron.d/", "/systemd/", "/init.d/")):
        return PathSensitivity.CRITICAL
    if text.startswith(("/usr/local/bin/", "/opt/", "/home/")):
        return PathSensitivity.HIGH
    if "/tmp/" in text or "/var/tmp/" in text or "tmp" in parts:
        return PathSensitivity.HIGH
    if path.name.startswith("."):
        return PathSensitivity.MEDIUM
    return PathSensitivity.LOW


def _read_header(path: Path, max_bytes: int = 256) -> bytes:
    try:
        with path.open("rb") as handle:
            return handle.read(max_bytes)
    except (OSError, PermissionError):
        return b""


def is_binary(path: Path) -> bool:
    header = _read_header(path, 1024)
    return bool(header and b"\x00" in header)


def classify_artifact(path: Path, metadata: FileMetadata) -> ArtifactType:
    name = path.name
    lower_name = name.lower()
    suffix = path.suffix.lower()
    text = path.as_posix().lower()

    if lower_name in {"sshd_config", "ssh_config"}:
        return ArtifactType.SSH_CONFIG
    if lower_name in STARTUP_NAMES or "/profile.d/" in text:
        return ArtifactType.STARTUP_HOOK
    if (
        "cron" in {part.lower() for part in path.parts}
        or any(
            segment in text
            for segment in ("/cron.d/", "/cron.daily/", "/cron.hourly/", "/spool/cron/")
        )
        or lower_name == "crontab"
    ):
        return ArtifactType.CRON
    if suffix in SYSTEMD_SUFFIXES or "/systemd/" in text:
        return ArtifactType.SYSTEMD_UNIT
    if is_binary(path):
        return ArtifactType.BINARY

    header = _read_header(path).decode("utf-8", errors="ignore")
    first_line = header.splitlines()[0] if header.splitlines() else ""
    if (
        suffix in {".sh", ".bash", ".zsh", ".ksh"}
        or "sh" in first_line
        and first_line.startswith("#!")
    ):
        return ArtifactType.SHELL_SCRIPT
    if suffix == ".py" or (first_line.startswith("#!") and "python" in first_line):
        return ArtifactType.PYTHON_SCRIPT
    if suffix in CONFIG_SUFFIXES:
        return ArtifactType.CONFIG
    if name.startswith(".") and metadata.is_executable:
        return ArtifactType.HIDDEN_EXECUTABLE
    return ArtifactType.UNKNOWN
