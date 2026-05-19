# ── Stage 1: dependency builder ────────────────────────────────────────────
FROM python:3.10-slim AS builder

WORKDIR /build

# Install build tools (needed for some C-extension wheels)
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt --target=/build/deps

# ── Stage 2: minimal runtime ───────────────────────────────────────────────
FROM python:3.10-slim AS runtime

WORKDIR /app

# Non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Copy installed packages
COPY --from=builder /build/deps /usr/local/lib/python3.10/site-packages

# Copy application code
COPY app/ ./app/

RUN mkdir -p logs && chown -R appuser:appgroup /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1        \
    PYTHONPATH=/app

USER appuser

EXPOSE 8000

# Graceful shutdown support
STOPSIGNAL SIGTERM

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--log-config", "/dev/null"]
