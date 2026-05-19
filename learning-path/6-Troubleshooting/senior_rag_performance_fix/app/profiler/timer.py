"""
app/profiler/timer.py

Async-safe stage timer for RAG pipelines.

Usage:
    timer = PipelineTimer()
    async with timer.stage("retrieval"):
        ...
    async with timer.stage("reranking"):
        ...
    report = timer.report()   # → dict with _time_ms for each stage
"""
from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncGenerator

logger = logging.getLogger("profiler.timer")


@dataclass
class StageResult:
    name: str
    start_time: float = field(default_factory=time.perf_counter)
    end_time: float = 0.0
    duration_ms: float = 0.0

    def finish(self) -> None:
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1_000


class PipelineTimer:
    """Tracks wall-clock time per named stage in a RAG pipeline."""

    def __init__(self) -> None:
        self._stages: dict[str, StageResult] = {}
        self._pipeline_start = time.perf_counter()

    @asynccontextmanager
    async def stage(self, name: str) -> AsyncGenerator[None, None]:
        result = StageResult(name=name)
        try:
            yield
        finally:
            result.finish()
            self._stages[name] = result
            logger.info(
                "stage_complete | stage=%s | duration_ms=%.2f",
                name,
                result.duration_ms,
            )

    def report(self) -> dict:
        total_ms = (time.perf_counter() - self._pipeline_start) * 1_000
        payload = {f"{name}_time_ms": round(r.duration_ms, 2) for name, r in self._stages.items()}
        payload["total_time_ms"] = round(total_ms, 2)
        return payload
