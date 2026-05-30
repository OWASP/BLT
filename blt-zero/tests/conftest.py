import sys
from unittest.mock import MagicMock

# Stub Cloudflare runtime modules that don't exist in standard CPython so that
# imports from src/ work under pytest without the Workers runtime.
sys.modules.setdefault("workers", MagicMock())
sys.modules.setdefault("js", MagicMock())

