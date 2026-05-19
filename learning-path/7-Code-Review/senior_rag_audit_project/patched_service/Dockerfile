# patched_service/Dockerfile — Production-Grade Multi-Stage Build

# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build
RUN pip install --no-cache-dir --upgrade pip

COPY patched_service/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: runtime (minimal image) ─────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="RAG AI Service"
LABEL org.opencontainers.image.version="2.0.0"

WORKDIR /app

# SEC: непривилегированный пользователь
RUN groupadd --gid 1000 appgroup && \
    useradd  --uid 1000 --gid appgroup --no-create-home appuser

COPY --from=builder /install /usr/local
COPY patched_service/app ./app

# SEC: только нужные разрешения
RUN chown -R appuser:appgroup /app
USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

EXPOSE 8000

# RESILIENCE: healthcheck внутри образа
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "2", "--loop", "uvloop", "--http", "h11"]
