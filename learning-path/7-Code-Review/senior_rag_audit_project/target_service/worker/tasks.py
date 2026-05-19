"""
target_service/worker/tasks.py — Celery воркер для фоновых задач.
"""
from celery import Celery                      #! SCALE: жёсткий лимит
import psycopg2                                #! SCALE: синхронный драйвер

REDIS_URL = "redis://:hardcoded_redis_pass@redis:6379"  #! SEC

celery_app = Celery("rag_tasks", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.worker_concurrency = 4         #! SCALE: хардкод, нет динамики


@celery_app.task(bind=True)
def process_embedding(self, doc_id: int, content: str):
    """Генерация эмбеддинга — синхронный пулинг задач."""
    import time
    time.sleep(0.5)                            #! SCALE: синхронный blocking sleep
    # Нет retry-логики                         #! RESILIENCE
    # Нет трассировки                          #! OBS
    print(f"Processing doc {doc_id}")          #! OBS: print вместо структурированного лога
    return {"doc_id": doc_id, "status": "embedded"}
