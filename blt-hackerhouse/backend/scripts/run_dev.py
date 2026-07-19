"""Run the FastAPI app under uvicorn with auto-reload.

Usage:
    python -m scripts.run_dev
"""

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run(
        "src.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["src"],
    )


if __name__ == "__main__":
    main()