"""
target_service/app/main.py
──────────────────────────────────────────────────────────────────────────────
RAG/LLM сервис — AUDIT TARGET.
Содержит намеренные архитектурные проблемы, помеченные категориями:
  #! SCALE   — масштабируемость
  #! RESILIENCE — отказоустойчивость
  #! OBS     — observability
  #! SEC     — безопасность
  #! MAINT   — maintainability
  #! COST    — стоимость инфраструктуры
──────────────────────────────────────────────────────────────────────────────
"""

import os
import time
import logging

from fastapi import FastAPI, Request
from openai import OpenAI                      #! SCALE+RESILIENCE: синхронный клиент
import psycopg2                                #! SCALE: синхронный драйвер БД
import redis                                   #! RESILIENCE: нет retry/circuit-breaker
from celery import Celery                      #! SCALE: жёсткий лимит воркеров

# ─── SEC: секреты захардкожены, не из K8s Secrets / Vault ────────────────────
OPENAI_API_KEY = "sk-hardcoded-openai-key-prod-1234"   #! SEC: в коде + в git
POSTGRES_URL   = "postgresql://admin:admin123@db:5432/ragdb"  #! SEC
REDIS_URL      = "redis://:hardcoded_redis_pass@redis:6379"   #! SEC

# ─── OBS: стандартный текстовый logger, нет Trace-ID ─────────────────────────
logging.basicConfig(
    filename="/var/log/rag_service.log",       #! OBS: файл вместо stdout/JSON
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",  #! OBS: нет trace_id, нет структуры
)
logger = logging.getLogger(__name__)

# ─── SCALE: Celery с жёстко заданным числом воркеров ─────────────────────────
celery_app = Celery(
    "rag_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
)
celery_app.conf.worker_concurrency = 4         #! SCALE: хардкод, нет автоскейла

app = FastAPI()

# ─── RESILIENCE: нет Liveness/Readiness пробы ────────────────────────────────
# (health endpoint отсутствует полностью)      #! RESILIENCE


@app.post("/rag/query")
def rag_query(request: Request):               #! SCALE: синхронный def в FastAPI
    """RAG query — поиск + LLM генерация."""
    import json
    body = request.body()                      #! MAINT: неверный вызов (нет await)
    data = json.loads(body)
    query = data.get("query", "")

    logger.info(f"Query received: {query}")    #! OBS: PII в логах, нет trace_id

    # ─── COST: нет семантического кэша — каждый похожий запрос идёт в LLM ────
    r = redis.from_url(REDIS_URL)              #! RESILIENCE: нет retry; COST: нет semantic cache
    cached = r.get(f"exact:{query}")           #! COST: только точное совпадение
    if cached:
        return {"response": cached.decode(), "cached": True}

    # ─── RESILIENCE: нет retry, нет circuit-breaker ──────────────────────────
    client = OpenAI(api_key=OPENAI_API_KEY)    #! SCALE: новый клиент на каждый запрос
    try:
        resp = client.chat.completions.create( #! RESILIENCE: нет retry при 429/500
            model="gpt-4o",
            messages=[{"role": "user", "content": query}],
        )
        answer = resp.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI error: {e}")     #! OBS: нет trace_id, нет метрик
        return {"error": str(e)}               #! SEC: внутренняя ошибка клиенту

    # ─── COST: нет учёта токенов / стоимости ─────────────────────────────────
    # logger.info(f"tokens={resp.usage.total_tokens}")  # закомментировано!  #! COST+OBS

    r.set(f"exact:{query}", answer, ex=60)     #! COST: TTL 60s — слишком короткий
    return {"response": answer, "cached": False}


@app.post("/rag/ingest")
def ingest_documents(request: Request):        #! SCALE: синхронная загрузка в запросе
    """Синхронная загрузка документов — блокирует поток."""
    import json
    body = request.body()
    data = json.loads(body)

    # ─── MAINT: сырой SQL прямо в роутере ───────────────────────────────────
    conn = psycopg2.connect(POSTGRES_URL)      #! SCALE: синхронное соединение
    cur = conn.cursor()
    for doc in data.get("documents", []):
        # ─── SEC: SQL-инъекция ───────────────────────────────────────────────
        cur.execute(f"INSERT INTO documents (content) VALUES ('{doc['content']}')")  #! SEC
    conn.commit()
    conn.close()                               #! SCALE: нет пула соединений

    logger.info(f"Ingested {len(data.get('documents',[]))} docs")
    return {"status": "ok"}


@app.get("/rag/status")
def status():                                  #! OBS: нет метрик Prometheus
    """Минимальный статус без метрик."""
    return {"status": "running"}               #! RESILIENCE: нет health checks для K8s
