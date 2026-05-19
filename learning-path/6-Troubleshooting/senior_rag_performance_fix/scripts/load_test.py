#!/usr/bin/env python3
"""
scripts/load_test.py
Minimal async load tester using httpx.
Sends N concurrent requests to both /ask and /ask-optimized,
prints per-request timings and a summary table.

Usage:
    python scripts/load_test.py --concurrency 5 --requests 10 --host http://localhost:8080
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time

import httpx

PAYLOAD = {"query": "How does RAG improve LLM accuracy?", "top_k": 3}
TIMEOUT = 120.0


async def single_request(client: httpx.AsyncClient, url: str, idx: int) -> dict:
    start = time.perf_counter()
    try:
        resp = await client.post(url, json=PAYLOAD, timeout=TIMEOUT)
        elapsed = (time.perf_counter() - start) * 1000
        status = resp.status_code
        timings = {}
        if status == 200:
            body = resp.json()
            timings = body.get("timings", {})
        return {"idx": idx, "status": status, "total_ms": round(elapsed, 1), "timings": timings}
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return {"idx": idx, "status": "ERROR", "error": str(exc), "total_ms": round(elapsed, 1)}


async def run_load_test(host: str, endpoint: str, concurrency: int, n_requests: int):
    url = f"{host}{endpoint}"
    print(f"\n{'='*60}")
    print(f"  Endpoint : {url}")
    print(f"  Requests : {n_requests}  |  Concurrency: {concurrency}")
    print(f"{'='*60}")

    async with httpx.AsyncClient() as client:
        semaphore = asyncio.Semaphore(concurrency)

        async def bounded(idx):
            async with semaphore:
                return await single_request(client, url, idx)

        results = await asyncio.gather(*[bounded(i) for i in range(n_requests)])

    successes = [r for r in results if r["status"] == 200]
    failures  = [r for r in results if r["status"] != 200]
    times_ms  = [r["total_ms"] for r in successes]

    print(f"  ✅ Successes : {len(successes)}")
    print(f"  ❌ Failures  : {len(failures)}")
    if times_ms:
        print(f"  Latency p50  : {statistics.median(times_ms):.0f} ms")
        print(f"  Latency p95  : {sorted(times_ms)[int(len(times_ms)*0.95)]:.0f} ms")
        print(f"  Latency max  : {max(times_ms):.0f} ms")

    if successes:
        sample = successes[0].get("timings", {})
        if sample:
            print(f"  Sample timings (first success):")
            for k, v in sample.items():
                print(f"    {k}: {v} ms")

    if failures:
        print(f"  First failure: {json.dumps(failures[0])}")
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8080")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--requests", type=int, default=6)
    parser.add_argument(
        "--endpoint",
        choices=["buggy", "optimized", "both"],
        default="both",
    )
    args = parser.parse_args()

    async def run_all():
        if args.endpoint in ("buggy", "both"):
            print("\n⚠️  Testing BUGGY endpoint (expect high latency / 504 errors via Nginx)...")
            await run_load_test(args.host, "/ask", args.concurrency, args.requests)
        if args.endpoint in ("optimized", "both"):
            print("\n✅  Testing OPTIMIZED endpoint...")
            await run_load_test(args.host, "/ask-optimized", args.concurrency, args.requests)

    asyncio.run(run_all())


if __name__ == "__main__":
    main()
