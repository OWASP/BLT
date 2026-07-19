from __future__ import annotations

import os
import stat
from pathlib import Path

from blt_mayo.models.artifact import FileMetadata

try:  # Unix/Linux owner and group resolution.
    import grp
    import pwd
except ImportError:  # pragma: no cover - exercised on Windows only.
    grp = None  # type: ignore[assignment]
    pwd = None  # type: ignore[assignment]


def _owner_name(identifier: int) -> str | None:
    if pwd is None:
        return None
    try:
        return pwd.getpwuid(identifier).pw_name
    except KeyError:
        return None


def _group_name(identifier: int) -> str | None:
    if grp is None:
        return None
    try:
        return grp.getgrgid(identifier).gr_name
    except KeyError:
        return None


def extract_metadata(path: Path, follow_symlinks: bool = False) -> FileMetadata:
    result = path.stat() if follow_symlinks else path.lstat()
    mode = stat.S_IMODE(result.st_mode)
    is_symlink = path.is_symlink()
    symlink_target: str | None = None
    if is_symlink:
        try:
            symlink_target = os.readlink(path)
        except OSError:
            symlink_target = None
    return FileMetadata(
        owner=_owner_name(result.st_uid),
        group=_group_name(result.st_gid),
        uid=result.st_uid,
        gid=result.st_gid,
        mode=mode,
        permissions=stat.filemode(result.st_mode),
        size=result.st_size,
        modified_at=result.st_mtime,
        created_at=result.st_ctime,
        is_symlink=is_symlink,
        symlink_target=symlink_target,
        is_executable=bool(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)),
        is_world_writable=bool(mode & stat.S_IWOTH),
        is_group_writable=bool(mode & stat.S_IWGRP),
    )
