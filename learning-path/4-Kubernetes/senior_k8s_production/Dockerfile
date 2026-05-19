# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build
COPY app/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim

# Non-root user
RUN addgroup --system appgroup  && adduser  --system --ingroup appgroup --no-create-home appuser

WORKDIR /app

COPY --from=builder /install /usr/local
COPY app/main.py .

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3     CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "main:app",      "--host", "0.0.0.0",      "--port", "8000",      "--workers", "2",      "--log-level", "info"]
