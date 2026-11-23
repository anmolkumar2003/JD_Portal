"""Add any missing reference data (stages, email templates, departments). Safe to re-run."""

import asyncio
import sys

from app.core.db import SessionLocal, engine
from app.reference_data import ensure_org, ensure_reference_data


async def _run() -> int:
    async with SessionLocal() as session:
        org = await ensure_org(session)
        result = await ensure_reference_data(session, org)
        await session.commit()
    await engine.dispose()
    print(f"{org.name}: {result}")
    return 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    sys.exit(main())
