# target_service/Dockerfile
# ─── AUDIT TARGET: проблемный Dockerfile ─────────────────────────────────────

FROM python:3.10                              # нет -slim, огромный образ  #! COST+MAINT

# SEC: запуск от root                         #! SEC
# USER root (по умолчанию)

WORKDIR /app

# MAINT: нет разделения на слои кэша           #! MAINT+COST
COPY . .
RUN pip install -r requirements.txt

# SEC: секреты в ENV внутри образа             #! SEC
ENV OPENAI_API_KEY=sk-hardcoded-openai-key-prod-1234
ENV POSTGRES_URL=postgresql://admin:admin123@db:5432/ragdb
ENV REDIS_URL=redis://:hardcoded_redis_pass@redis:6379

EXPOSE 8000

# OBS: нет health check                        #! RESILIENCE+OBS
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
