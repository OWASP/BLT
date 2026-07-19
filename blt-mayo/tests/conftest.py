from __future__ import annotations

from pathlib import Path

import pytest

from blt_mayo.config.models import ScanConfig


@pytest.fixture()
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture()
def scan_config() -> ScanConfig:
    return ScanConfig(max_depth=10, max_file_size=1_000_000)
