"""patched_service/app/metrics.py
Prometheus-метрики: бизнес (токены, стоимость) + технические (latency, cache).
"""

from prometheus_client import Counter, Histogram, Gauge

LLM_REQUESTS_TOTAL = Counter(
    "llm_requests_total",
    "Общее число LLM-запросов",
    ["status", "model"],
)

LLM_TOKENS_TOTAL = Counter(
    "llm_tokens_total",
    "Суммарное число токенов",
    ["type", "model"],   # type: input / output
)

LLM_COST_USD = Counter(
    "llm_cost_usd_total",
    "Суммарная стоимость LLM-запросов в USD",
    ["model"],
)

LLM_LATENCY = Histogram(
    "llm_latency_seconds",
    "Latency LLM-вызовов",
    ["model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

CACHE_HIT_RATIO = Gauge(
    "cache_hit_ratio",
    "Доля запросов, отвеченных из кэша",
)

CIRCUIT_BREAKER_STATE = Gauge(
    "circuit_breaker_state",
    "Состояние Circuit Breaker (0=closed, 1=half_open, 2=open)",
    ["service"],
)
