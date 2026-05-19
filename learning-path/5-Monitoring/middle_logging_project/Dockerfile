# ── Stage 1: dependency layer ─────────────────────────────────────────────
FROM python:3.10-slim AS deps

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ── Stage 2: runtime image ────────────────────────────────────────────────
FROM python:3.10-slim AS runtime

WORKDIR /app

COPY --from=deps /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

COPY app/ ./app/

# Create logs directory (may also be mounted via volume)
RUN mkdir -p logs

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1        \
    LOG_LEVEL=INFO            \
    LOG_TO_FILE=false

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
