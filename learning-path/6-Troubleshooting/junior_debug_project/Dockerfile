# ── Stage 1: base ────────────────────────────────────────────────────
FROM python:3.10-slim AS base

WORKDIR /app

# Системные зависимости (минимальный набор)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Зависимости Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Исходный код
COPY app/ ./app/

# Не запускаем от root
RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
