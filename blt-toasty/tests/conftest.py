import sys
import os
import importlib
import json
import glob
import pytest
from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# Fix the dual-module problem:  tests do `from src.errors import X` while
# source code does `from errors import X`.  Without this, Python loads two
# separate module objects and `pytest.raises` / `mock.patch` break.
#
# Solution: for every .py file in src/, ensure that both `src.<name>` and
# `<name>` point to the **same** module object in sys.modules.
# ---------------------------------------------------------------------------
_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)
_src_dir = os.path.join(_root_dir, "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

# Ensure `src` package is importable
import src as _src_pkg  # noqa: E402

for _fname in os.listdir(_src_dir):
    if _fname.endswith(".py") and _fname != "__init__.py":
        _mod_name = _fname[:-3]
        _src_mod_name = f"src.{_mod_name}"
        # If the bare module is already loaded, alias it
        if _mod_name in sys.modules and _src_mod_name not in sys.modules:
            sys.modules[_src_mod_name] = sys.modules[_mod_name]
            setattr(_src_pkg, _mod_name, sys.modules[_mod_name])
        # If the src.module is already loaded, alias the bare name
        elif _src_mod_name in sys.modules and _mod_name not in sys.modules:
            sys.modules[_mod_name] = sys.modules[_src_mod_name]
        # If neither is loaded yet, import the bare one and alias it
        elif _mod_name not in sys.modules and _src_mod_name not in sys.modules:
            try:
                _mod = importlib.import_module(_mod_name)
                sys.modules[_src_mod_name] = _mod
                setattr(_src_pkg, _mod_name, _mod)
            except Exception:
                pass  # some modules may fail to import outside Workers (e.g. js imports)


@pytest.fixture(scope="session")
def all_golden_reports():
    """
    Loads all JSON reports from both the historical and synthetic golden set directories.
    Returns a list of dictionaries.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    synthetic_files = glob.glob(os.path.join(base_dir, "golden_set", "synthetic", "*.json"))
    historical_files = glob.glob(os.path.join(base_dir, "golden_set", "historical", "*.json"))

    all_files = synthetic_files + historical_files
    reports = []

    for fpath in all_files:
        with open(fpath, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                # Store the file path in the dict for easier debugging if a test fails
                data["_filepath"] = fpath
                reports.append(data)
            except json.JSONDecodeError as e:
                pytest.fail(f"Failed to parse JSON in {fpath}: {str(e)}")

    return reports


def pytest_generate_tests(metafunc):
    """
    This tells Pytest to dynamically generate a test for EACH report in the golden set.
    Instead of running one big test 50 times, it creates 50 separate test cases.
    """
    if "golden_report" in metafunc.fixturenames:
        # We need to manually load the files here to parameterize the tests
        base_dir = os.path.dirname(os.path.abspath(__file__))
        synthetic_files = glob.glob(os.path.join(base_dir, "golden_set", "synthetic", "*.json"))
        historical_files = glob.glob(os.path.join(base_dir, "golden_set", "historical", "*.json"))
        all_files = synthetic_files + historical_files

        reports = []
        ids = []
        for fpath in all_files:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["_filepath"] = fpath
                reports.append(data)
                # Use the file name as the test ID
                ids.append(os.path.basename(fpath))

        metafunc.parametrize("golden_report", reports, ids=ids)


@pytest.fixture
def mock_d1():
    db = MagicMock()
    # Support traditional prepare().bind().run()
    db.prepare.return_value.bind.return_value.run = AsyncMock()
    db.prepare.return_value.bind.return_value.first = AsyncMock()
    # Mock db.batch()
    db.batch = AsyncMock()
    return db


@pytest.fixture
def mock_analytics():
    analytics = MagicMock()
    analytics.writeDataPoint = MagicMock()
    return analytics
