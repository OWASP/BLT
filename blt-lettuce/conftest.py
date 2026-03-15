"""Root conftest.py — add src/ to sys.path so that the 'lettuce' package
bundled inside src/ is importable when running tests from the project root."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
