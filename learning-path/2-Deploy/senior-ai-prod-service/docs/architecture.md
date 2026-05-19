# Architecture Overview

```
                    ┌─────────────────────────────────────────────┐
                    │              PRODUCTION VM                   │
                    │                                              │
 Client             │  ┌──────────┐     ┌───────────────────────┐ │
 ──────── HTTPS ───►│  │          │     │   FastAPI RAG Service  │ │
                    │  │  Nginx   │────►│                         │ │
                    │  │ :80/:443 │     │  /ask  (SSE stream)     │ │
                    │  │          │     │  /health /readiness     │ │
                    │  └──────────┘     │  /metrics (Prometheus)  │ │
                    │                  └──────────┬──────────────┘ │
                    │                             │                 │
                    │            ┌────────────────┼────────────┐    │
                    │            │  backend net   │            │    │
                    │            │  (internal)    │            │    │
                    │     ┌──────▼──────┐   ┌────▼──────┐     │    │
                    │     │ PostgreSQL  │   │   Redis   │     │    │
                    │     │  (asyncpg) │   │ (aioredis)│     │    │
                    │     │  history   │   │  sem.cache│     │    │
                    │     └────────────┘   └───────────┘     │    │
                    │                                          │    │
                    └──────────────────────────────────────────┘    │
                                                                     │
  RAG Pipeline:                                                      │
  Question ──► [Semantic Cache?] ──► [Vector Retrieval / FAISS]      │
          ──► [LangChain LCEL Chain] ──► [OpenAI LLM + Streaming]    │
          ──► [Cache Write + DB Log] ──► Client                      │
```

## Key Design Decisions

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Async DB | asyncpg + SQLAlchemy 2.0 | Non-blocking, 12-Factor |
| Vector store | FAISS (swap for pgvector) | Fast local dev; prod → pgvector |
| Caching | Redis + SHA-256 key | Sub-ms cache lookup |
| Streaming | FastAPI StreamingResponse (SSE) | Real-time UX |
| Observability | JSON logs + Prometheus | Grafana/Loki compatible |
| SSL | Nginx + Let's Encrypt (Certbot) | Industry standard |
| Zero-downtime | `--scale api=2` rolling | No K8s required |
