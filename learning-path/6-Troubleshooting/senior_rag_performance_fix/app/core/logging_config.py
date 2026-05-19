"""
app/core/logging_config.py
JSON-structured async-safe logging.
Uses a QueueHandler so disk I/O never touches the event loop.
"""
from __future__ import annotations

import logging
import logging.handlers
import queue
import sys
from app.core.config import settings


def setup_logging() -> None:
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Non-blocking queue listener — log records are emitted by the event loop
    # thread but written to stdout/stderr by a background thread.
    log_queue: queue.Queue = queue.Queue(maxsize=10_000)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )

    listener = logging.handlers.QueueListener(log_queue, stream_handler, respect_handler_level=True)
    listener.start()

    queue_handler = logging.handlers.QueueHandler(log_queue)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(queue_handler)
    root.setLevel(log_level)

    # Reduce third-party noise
    for noisy in ("uvicorn.access", "httpx", "httpcore", "faiss"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
