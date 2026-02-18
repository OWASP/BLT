"""
Pytest configuration file to set up test environment.
"""

import sys
from pathlib import Path

# Add src directory to Python path so imports work correctly
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
