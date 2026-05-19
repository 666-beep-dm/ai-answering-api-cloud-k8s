"""Prometheus RED metrics + token counter."""
from prometheus_client import Counter, Histogram, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST

REGISTRY = CollectorRegistry(auto_describe=True)

http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests",
    ["method", "endpoint", "status"], registry=REGISTRY,
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds", "HTTP request latency",
    ["method", "endpoint"], registry=REGISTRY,
)
llm_tokens_total = Counter(
    "llm_tokens_total", "LLM tokens consumed",
    ["type"], registry=REGISTRY,   # type: prompt | completion
)
upload_errors_total = Counter(
    "upload_errors_total", "Failed upload attempts",
    [], registry=REGISTRY,
)


def metrics_response():
    from fastapi.responses import Response
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
