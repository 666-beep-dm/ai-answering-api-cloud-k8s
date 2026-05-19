from prometheus_client import Counter, Histogram, Gauge, REGISTRY
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

# ── Counters ──────────────────────────────────────────────────────────────────
ask_requests_total = Counter(
    "ask_requests_total", "Total /ask requests", ["status"]
)
cache_hits_total = Counter(
    "cache_hits_total", "Semantic cache hits"
)
cache_misses_total = Counter(
    "cache_misses_total", "Semantic cache misses"
)

# ── Histograms ────────────────────────────────────────────────────────────────
ask_latency_seconds = Histogram(
    "ask_latency_seconds",
    "End-to-end /ask latency",
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)
retrieval_latency_seconds = Histogram(
    "retrieval_latency_seconds",
    "Vector retrieval stage latency",
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
)
llm_latency_seconds = Histogram(
    "llm_latency_seconds",
    "LLM generation latency",
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

# ── Gauges ────────────────────────────────────────────────────────────────────
active_streams = Gauge("active_streams", "Currently active SSE streams")


def metrics_endpoint() -> Response:
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )
