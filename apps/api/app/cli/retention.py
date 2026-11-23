"""Run the rejected-candidate retention job. No-op when RETENTION_REJECTED_DAYS=0.

docker compose -f docker-compose.prod.yml exec api python -m app.cli.retention
"""

import asyncio
import sys

from app.core.db import SessionLocal, engine
from app.services.retention import run_retention_rejected


async def _main() -> int:
    try:
        async with SessionLocal() as session:
            report = await run_retention_rejected(session)
        if not report.get("enabled", True):
            print("Retention disabled (RETENTION_REJECTED_DAYS=0).")
            return 0
        print(f"Processed {report.get('processed', 0)} candidate(s).")
        return 0
    finally:
        await engine.dispose()


def main() -> None:
    sys.exit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
