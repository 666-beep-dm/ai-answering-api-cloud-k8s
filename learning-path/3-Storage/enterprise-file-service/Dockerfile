# ══════════════════════════════════════════════════════════════════════════════
# Stage 1 — dependency builder
# ══════════════════════════════════════════════════════════════════════════════
FROM python:3.10-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends         gcc         libpq-dev         libmagic1     && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ══════════════════════════════════════════════════════════════════════════════
# Stage 2 — lean runtime image
# ══════════════════════════════════════════════════════════════════════════════
FROM python:3.10-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends         libpq5         libmagic1         curl     && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installed Python packages from builder
COPY --from=builder /install /usr/local

# Application source
COPY src/app ./app
COPY migrations ./migrations
COPY alembic.ini .

ENV PYTHONUNBUFFERED=1     PYTHONDONTWRITEBYTECODE=1     PYTHONPATH=/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3     CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
