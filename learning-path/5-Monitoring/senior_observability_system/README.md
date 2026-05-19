# FastAPI Senior Observability System

> **Enterprise-grade**, Cloud Native observability platform built on FastAPI —
> implementing the **Three Pillars**: Metrics · Logs · Traces.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Observability Stack                          │
│                                                                 │
│  HTTP Request                                                   │
│      │                                                          │
│      ▼                                                          │
│  ┌──────────────────────────────────┐                          │
│  │   ObservabilityMiddleware (ASGI) │                          │
│  │  • Generate / propagate IDs      │                          │
│  │  • Open OTel span                │                          │
│  │  • Start Prometheus in-flight    │                          │
│  └──────────┬───────────────────────┘                          │
│             │                                                   │
│      ┌──────▼──────────────────────┐                          │
│      │  FastAPI Exception Handlers  │  ← 4xx WARNING           │
│      │  (centralised, typed)        │  ← 5xx ERROR+stacktrace  │
│      └──────┬──────────────────────┘                          │
│             │                                                   │
│      ┌──────▼──────────────────────┐                          │
│      │      Route Handlers          │                          │
│      │  /success /slow /error …     │                          │
│      └──────┬──────────────────────┘                          │
│             │                                                   │
│      ┌──────▼──────────────────────┐                          │
│      │  Response (status captured) │                          │
│      └──────┬──────────────────────┘                          │
│             │                                                   │
│      ┌──────▼──────────────────────────────────────────┐      │
│      │ Middleware post-processing                        │      │
│      │  • Record Prometheus counter + histogram          │      │
│      │  • Inject X-Trace-ID / X-Request-ID headers      │      │
│      │  • Feed sliding-window alerting engine            │      │
│      │  • Close OTel span                               │      │
│      └──────────────────────────────────────────────────┘      │
│                                                                 │
│  Pillar 1 — Metrics   → GET /metrics → Prometheus scrapes      │
│  Pillar 2 — Logs      → stdout NDJSON → Vector/Fluentbit/Loki  │
│  Pillar 3 — Tracing   → OTel Console (dev) / OTLP (prod)       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Recommended Infrastructure Requirements

| Component | Minimum  | Recommended  |
|-----------|----------|--------------|
| CPU       | 2 cores  | **4+ cores** |
| RAM       | 8 GB     | **16 GB**    |
| Disk      | 10 GB    | 50 GB SSD    |
| OS        | Linux / macOS / WSL2 | — |
| Docker    | 24+      | latest       |
| Python    | 3.10     | 3.10+        |

---

## Project Structure

```
senior_observability_system/
├── app/
│   ├── api/
│   │   └── routes.py              # Endpoints + /metrics + /health
│   ├── core/
│   │   ├── config.py              # Pydantic-Settings v2 (all via .env)
│   │   └── exception_handlers.py  # 4xx→WARNING / 5xx→ERROR+stack_trace
│   └── observability/
│       ├── logger.py              # JSON formatter (Loki-ready)
│       ├── metrics.py             # Prometheus counters/histograms/gauges
│       ├── tracer.py              # OTel TracerProvider (console|otlp)
│       ├── middleware.py          # Pure ASGI unified observability layer
│       └── alerting.py           # Sliding-window alerting engine
├── prometheus/
│   ├── prometheus.yml             # Scrape config
│   └── alert.rules.yml            # HighErrorRate / HighLatency / ServiceDown
├── tests/
│   └── test_observability.py      # 8 async integration tests
├── logs/                          # Volume-mounted (docker-compose)
├── .env / .env.example
├── Dockerfile                     # Multi-stage, non-root user
├── docker-compose.yml             # API + Prometheus (resource-limited)
└── README.md
```

---

## The Three Pillars

### 1. Metrics (Prometheus)
| Metric | Type | Labels |
|--------|------|--------|
| `http_requests_total` | Counter | method, path, status |
| `http_request_duration_seconds` | Histogram | method, path |
| `http_requests_in_flight` | Gauge | method, path |
| `app_errors_total` | Counter | error_type, path |
| `app_info` | Info | version, environment, service |

**Buckets**: 5ms → 10ms → 25ms → 50ms → 100ms → 250ms → 500ms → 1s → 2.5s → 5s → 10s
→ enables P50 / P90 / P99 latency queries in Prometheus / Grafana.

### 2. Structured Logs (JSON / Loki-ready)
Every line is a valid NDJSON object:
```json
{
  "timestamp": "2024-05-01T12:00:01.000+00:00",
  "level": "INFO",
  "logger": "app.middleware",
  "message": "← GET /api/v1/success 200  1.23 ms",
  "service": "fastapi-observability",
  "environment": "development",
  "version": "1.0.0",
  "trace_id": "a1b2c3d4...",
  "span_id": "e5f6a7b8...",
  "request_id": "uuid4",
  "path": "/api/v1/success",
  "method": "GET",
  "status_code": 200,
  "execution_time_ms": 1.23
}
```
**Loki labels** (low-cardinality): `service`, `environment`, `level`
**Loki indexed fields**: `trace_id`, `request_id`, `status_code`, `path`

### 3. Distributed Tracing (OpenTelemetry)
- W3C TraceContext propagation (`traceparent` / `tracestate`)
- Inbound `X-Trace-ID` / `X-Request-ID` headers respected and echoed
- Console exporter (dev) → switch to OTLP for Jaeger / Grafana Tempo
- Spans include: `http.method`, `http.url`, `http.status_code`, `request_id`

### 4. Alerting (Dual-Layer)
| Layer | Mechanism | Latency |
|-------|-----------|---------|
| In-process | Sliding-window engine → CRITICAL log | ~10 s |
| Prometheus | `alert.rules.yml` → Alertmanager | ~30 s |

Triggers:
- **HighErrorRate**: 5xx > 5% of requests in 1-minute window
- **HighLatency**: P99 > 500ms over 5-minute window
- **ServiceDown**: `up` metric == 0 for 30s

---

## API Endpoints

| Method | Path | Expected | Purpose |
|--------|------|----------|---------|
| GET | `/api/v1/success` | 200 | Happy path + trace IDs in body |
| GET | `/api/v1/slow` | 200 | Random 50–800ms delay (latency testing) |
| GET | `/api/v1/client-error` | 400 | WARNING log |
| GET | `/api/v1/server-error` | 500 | ERROR log + stack trace |
| POST | `/api/v1/validate` | 422 | Pydantic validation error |
| GET | `/metrics` | 200 | Prometheus scrape endpoint |
| GET | `/health` | 200 | Liveness probe |
| GET | `/docs` | 200 | Swagger UI |

---

## Quick Start — Docker (Recommended)

```bash
# 1. Clone / unzip
cd senior_observability_system

# 2. Configure
cp .env.example .env

# 3. Build and launch
docker-compose up --build -d

# 4. Verify services
docker-compose ps

# 5. Live JSON logs (pipe through jq for pretty-print)
docker-compose logs -f api | jq .

# 6. Open interfaces
#   Swagger UI:        http://localhost:8000/docs
#   Prometheus UI:     http://localhost:9090
#   Metrics raw:       http://localhost:8000/metrics
```

### Load Generation (trigger alerts)

```bash
# Generate mixed traffic — success, slow, errors
for i in $(seq 1 50); do
  curl -s http://localhost:8000/api/v1/success > /dev/null
  curl -s http://localhost:8000/api/v1/slow    > /dev/null
  sleep 0.1
done

# Spam 500 errors to trigger HighErrorRate alert
for i in $(seq 1 20); do
  curl -s http://localhost:8000/api/v1/server-error > /dev/null
done

# Query Prometheus — error rate
curl -s 'http://localhost:9090/api/v1/query?query=rate(http_requests_total{status=~"5.."}[1m])' | jq .

# Query P99 latency
curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.99,rate(http_request_duration_seconds_bucket[5m]))' | jq .
```

---

## Quick Start — Local (No Docker)

```bash
python -m venv .venv
source .venv/Scripts/activate   # Git Bash / Windows
# source .venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## Tests

```bash
pytest tests/ -v
# Expected: 8 passed
```

---

## Git Bash — Initialise & Push

```bash
git init
git add .
git commit -m "feat: senior enterprise-grade observability foundation"

git remote add origin https://github.com/<your-username>/senior_observability_system.git
git branch -M main
git push -u origin main
```

---

## Production Upgrade Path

| Feature | Dev (this repo) | Production addition |
|---------|-----------------|---------------------|
| Traces  | Console exporter | OTLP → Grafana Tempo / Jaeger |
| Logs    | stdout NDJSON | Vector → Loki |
| Metrics | `/metrics` | Prometheus + Grafana dashboards |
| Alerts  | In-process + rules file | Alertmanager → Slack / PagerDuty |
| Scaling | Single instance | Kubernetes + HPA |

---

## Resource Limits (docker-compose)

| Service | CPU limit | RAM limit |
|---------|-----------|-----------|
| api | 1.0 core | 512 MB |
| prometheus | 0.5 core | **384 MB** (hard cap) |

---

## License

MIT
