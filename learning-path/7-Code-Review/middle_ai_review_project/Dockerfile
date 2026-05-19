# ─── Stage 1: builder ────────────────────────────────────────────────────────
FROM python:3.10-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir --upgrade pip

COPY production_service/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─── Stage 2: runtime ────────────────────────────────────────────────────────
FROM python:3.10-slim AS runtime

WORKDIR /app

# Копируем только установленные пакеты из builder
COPY --from=builder /install /usr/local

# Копируем исходники приложения
COPY production_service/app ./app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
