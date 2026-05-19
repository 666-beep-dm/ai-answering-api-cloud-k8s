"""
In-process alerting engine (sliding window).

Fires structured WARNING / CRITICAL log events when:
  • Error rate (5xx / total)  > ALERT_ERROR_RATE_THRESHOLD (default 5 %)
  • P99 latency               > ALERT_LATENCY_THRESHOLD_MS  (default 500 ms)

Architecture note:
  In a production setup these thresholds live in Prometheus alerting rules
  (alert.rules.yml) and fire via Alertmanager → PagerDuty / Slack.
  This in-process engine provides an additional fast-path alert that is
  visible in the structured log stream and requires zero external deps.
"""

from __future__ import annotations

import asyncio
import collections
import logging
import time
from dataclasses import dataclass, field
from typing import Deque

from app.core.config import get_settings

_settings = get_settings()
_log      = logging.getLogger("app.alerting")


@dataclass
class _RequestSample:
    ts:          float
    status_code: int
    duration_ms: float
    path:        str
    method:      str


class SlidingWindowAlerting:
    """
    Thread/coroutine-safe sliding-window alert evaluator.
    Call .record() from the request middleware and
    .evaluate() periodically (background task).
    """

    def __init__(self) -> None:
        self._window: Deque[_RequestSample] = collections.deque()
        self._lock = asyncio.Lock()

    async def record(
        self,
        status_code: int,
        duration_ms: float,
        path: str,
        method: str,
    ) -> None:
        now = time.monotonic()
        sample = _RequestSample(
            ts=now,
            status_code=status_code,
            duration_ms=duration_ms,
            path=path,
            method=method,
        )
        async with self._lock:
            self._window.append(sample)
            # Evict samples outside the window
            cutoff = now - _settings.alert_window_seconds
            while self._window and self._window[0].ts < cutoff:
                self._window.popleft()

    async def evaluate(self) -> None:
        """Evaluate all alert rules; log CRITICAL if any fires."""
        async with self._lock:
            samples = list(self._window)

        if not samples:
            return

        total  = len(samples)
        errors = sum(1 for s in samples if s.status_code >= 500)
        error_rate = errors / total

        latencies = sorted(s.duration_ms for s in samples)
        p99_idx   = max(0, int(len(latencies) * 0.99) - 1)
        p99_ms    = latencies[p99_idx]

        extra = {
            "trace_id":    "alerting",
            "span_id":     "0",
            "request_id":  "alerting",
            "path":        "-",
            "method":      "-",
        }

        if error_rate > _settings.alert_error_rate_threshold:
            _log.critical(
                "ALERT FIRED — high 5xx error rate: %.1f%% (threshold %.1f%%) "
                "over last %ds window  [total=%d errors=%d]",
                error_rate * 100,
                _settings.alert_error_rate_threshold * 100,
                _settings.alert_window_seconds,
                total, errors,
                extra={**extra, "alert_name": "HighErrorRate",
                       "value": round(error_rate, 4),
                       "threshold": _settings.alert_error_rate_threshold},
            )

        if p99_ms > _settings.alert_latency_threshold_ms:
            _log.critical(
                "ALERT FIRED — high P99 latency: %.1f ms (threshold %.1f ms) "
                "over last %ds window  [samples=%d]",
                p99_ms,
                _settings.alert_latency_threshold_ms,
                _settings.alert_window_seconds,
                total,
                extra={**extra, "alert_name": "HighLatency",
                       "value": round(p99_ms, 2),
                       "threshold": _settings.alert_latency_threshold_ms},
            )


# Module-level singleton
alerting_engine = SlidingWindowAlerting()


async def alerting_background_task() -> None:
    """Periodic evaluator — run as asyncio background task."""
    interval = max(10, _settings.alert_window_seconds // 6)
    while True:
        await asyncio.sleep(interval)
        await alerting_engine.evaluate()
