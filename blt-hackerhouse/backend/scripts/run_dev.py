"""Run the FastAPI app under uvicorn with auto-reload (legacy local dev).

Requires uvicorn: pip install uvicorn[standard]

Usage:
    uv run python scripts/run_dev.py
"""

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run(
        "src.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["src"],
    )


if __name__ == "__main__":
    main()
