"""Apply pending database migrations.

Usage:
    python -m scripts.migrate
"""

from __future__ import annotations

import asyncio

from src.core.logging import configure_logging, get_logger
from src.storage import get_database


logger = get_logger(__name__)


async def main() -> int:
    configure_logging()
    db = get_database()
    await db.connect()
    try:
        applied = await db.run_migrations()
        logger.info("migrations finished", extra={"applied": applied})
    finally:
        await db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))