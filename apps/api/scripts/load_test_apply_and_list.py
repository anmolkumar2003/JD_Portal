#!/usr/bin/env python3
"""Light load probe for applications list and public apply (local dev).

Usage (stack running, migrations + seed applied):

    cd apps/api && python scripts/load_test_apply_and_list.py
    python scripts/load_test_apply_and_list.py --list-requests 40 --apply-requests 8
"""

from __future__ import annotations

import argparse
import asyncio
import os
import statistics
import time
import uuid
from dataclasses import dataclass, field

import httpx

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
DEFAULT_API = "http://localhost:8001/api/v1"
DEFAULT_EMAIL = os.environ.get("DEMO_LOGIN_EMAIL", "recruiter@demo.example.com")
DEFAULT_PASSWORD = os.environ.get("DEMO_PASSWORD", "")
DEFAULT_JOB_SLUG = "senior-android-developer"


@dataclass
class Timings:
    samples_ms: list[float] = field(default_factory=list)

    def record(self, started: float) -> None:
        self.samples_ms.append((time.perf_counter() - started) * 1000)

    def summary(self) -> str:
        if not self.samples_ms:
            return "no samples"
        sorted_ms = sorted(self.samples_ms)
        p95 = sorted_ms[int(0.95 * (len(sorted_ms) - 1))]
        return (
            f"n={len(sorted_ms)} "
            f"mean={statistics.mean(sorted_ms):.1f}ms "
            f"p50={statistics.median(sorted_ms):.1f}ms "
            f"p95={p95:.1f}ms "
            f"max={max(sorted_ms):.1f}ms"
        )


async def login(client: httpx.AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    return str(token)


async def run_list_load(
    client: httpx.AsyncClient, token: str, *, requests: int, concurrency: int
) -> Timings:
    sem = asyncio.Semaphore(concurrency)
    timings = Timings()
    headers = {"Authorization": f"Bearer {token}"}

    async def one(page: int) -> None:
        async with sem:
            started = time.perf_counter()
            response = await client.get(
                "/applications",
                headers=headers,
                params={"page": page, "page_size": 20, "sort": "-applied_at"},
            )
            response.raise_for_status()
            timings.record(started)

    await asyncio.gather(*(one(i % 5 + 1) for i in range(requests)))
    return timings


async def run_apply_load(
    client: httpx.AsyncClient, *, requests: int, concurrency: int, slug: str
) -> Timings:
    sem = asyncio.Semaphore(concurrency)
    timings = Timings()

    async def one(idx: int) -> None:
        async with sem:
            started = time.perf_counter()
            unique = f"load-{uuid.uuid4().hex[:10]}-{idx}@mail.example.com"
            data = {
                "first_name": "Load",
                "last_name": f"Test{idx}",
                "email": unique,
                "phone": "+91 98765 43210",
                "current_company": "Load Co",
                "consent": "true",
                "website": "",
            }
            files = {"cv": ("load-test.pdf", PDF, "application/pdf")}
            response = await client.post(f"/public/jobs/{slug}/apply", data=data, files=files)
            response.raise_for_status()
            timings.record(started)

    await asyncio.gather(*(one(i) for i in range(requests)))
    return timings


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default=DEFAULT_API)
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--job-slug", default=DEFAULT_JOB_SLUG)
    parser.add_argument("--list-requests", type=int, default=30)
    parser.add_argument("--apply-requests", type=int, default=5)
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()

    async with httpx.AsyncClient(base_url=args.api_base, timeout=60.0) as client:
        token = await login(client, args.email, args.password)
        list_timings = await run_list_load(
            client, token, requests=args.list_requests, concurrency=args.concurrency
        )
        apply_timings = await run_apply_load(
            client,
            requests=args.apply_requests,
            concurrency=min(args.concurrency, args.apply_requests),
            slug=args.job_slug,
        )

    print(f"GET /applications: {list_timings.summary()}")
    print(f"POST /public/jobs/{{slug}}/apply: {apply_timings.summary()}")


if __name__ == "__main__":
    asyncio.run(main())
