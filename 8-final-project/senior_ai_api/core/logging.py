"""Structured JSON logging with X-Trace-ID propagation."""
import json, logging, os
from datetime import datetime, timezone
from contextvars import ContextVar

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")


class _JsonFormatter(logging.Formatter):
    def format(self, r: logging.LogRecord) -> str:
        obj = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": r.levelname,
            "logger": r.name,
            "trace_id": trace_id_var.get(),
            "msg": r.getMessage(),
        }
        if r.exc_info:
            obj["exc"] = self.formatException(r.exc_info)
        return json.dumps(obj, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    fmt = _JsonFormatter()
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root = logging.getLogger()
    root.handlers = [sh]
    root.setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
