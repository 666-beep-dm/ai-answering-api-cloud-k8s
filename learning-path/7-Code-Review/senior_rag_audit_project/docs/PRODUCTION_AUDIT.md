# Production Readiness Audit Report
## RAG/LLM Enterprise AI Service

---

**Аудитор:** Principal Enterprise Architect / Lead MLOps Engineer
**Дата аудита:** 2024
**Компонент:** FastAPI RAG-сервис (OpenAI + Redis + PostgreSQL + Celery)
**Методология:** 12-Factor App · Cloud Native · OWASP · Google SRE Book

---

## Executive Summary

В ходе аудита выявлено **6 критических блокеров** выхода в production,
**12 major-проблем** и **8 minor** технических долгов.
Текущее состояние кодовой базы категорически непригодно для промышленной эксплуатации:
архитектурные уязвимости создают риски полной потери данных, утечки секретов и
неконтролируемых расходов на LLM API.

Рекомендуемое решение: применение патча (patched_service/) с поэтапной миграцией.

---

## Классификация проблем

### 🔴 CRITICAL — Production Blockers (блокирует релиз)

| ID | Категория | Описание | Файл |
|----|-----------|----------|------|
| C-1 | Безопасность | API-ключи и пароли БД захардкожены в Deployment YAML и Dockerfile | k8s/target/deployment.yaml |
| C-2 | Безопасность | SQL-инъекция в `/rag/ingest` через f-string конкатенацию | target_service/app/main.py:54 |
| C-3 | Отказоустойчивость | Redis и PostgreSQL без Persistent Volumes: полная потеря данных при рестарте пода | k8s/target/deployment.yaml |
| C-4 | Безопасность | Контейнеры запускаются от root (нет `runAsNonRoot`) | target_service/Dockerfile |
| C-5 | Отказоустойчивость | Нет Liveness/Readiness проб: K8s не может определить состояние пода | k8s/target/deployment.yaml |
| C-6 | Безопасность | Redis и PostgreSQL Services без NetworkPolicy: доступны всем подам кластера | k8s/target/service.yaml |

### 🟠 MAJOR — First Sprint (требует исправления в первом спринте)

| ID | Категория | Описание |
|----|-----------|----------|
| M-1 | Масштабируемость | Нет HPA: при пиковой нагрузке единственная реплика падает |
| M-2 | Масштабируемость | Синхронный OpenAI-клиент блокирует event loop FastAPI |
| M-3 | Масштабируемость | psycopg2 (синхронный) вместо asyncpg/SQLAlchemy async |
| M-4 | Отказоустойчивость | Нет Circuit Breaker и Retry для OpenAI API: один 429 ронит сервис |
| M-5 | Observability | Логирование через print/файл вместо структурированного JSON в stdout |
| M-6 | Observability | Нет Trace-ID: невозможно отследить запрос через сервисы |
| M-7 | Стоимость | Нет семантического кэша: каждый похожий запрос -> платный вызов LLM |
| M-8 | Стоимость | Нет учёта токенов и стоимости: бюджет неконтролируем |
| M-9 | CI/CD | Секреты передаются в build args (видны в логах CI) |
| M-10 | CI/CD | Нет линтинга, тестирования и SAST-сканирования в пайплайне |
| M-11 | CI/CD | Деплой в продакшн без approval gate при любом пуше |
| M-12 | Безопасность | Внутренние ошибки (stack trace) возвращаются клиенту |

### 🟡 MINOR — Technical Debt

| ID | Категория | Описание |
|----|-----------|----------|
| T-1 | Maintainability | Монолитный main.py: роутеры, бизнес-логика, SQL в одном файле |
| T-2 | Maintainability | Celery concurrency = 4 хардкодом, нет динамической настройки |
| T-3 | Observability | Нет бизнес-метрик в Prometheus (tokens/sec, cost/day) |
| T-4 | Observability | Нет алертинга по аномальным расходам |
| T-5 | Стоимость | LoadBalancer для dev-окружения (дорого) |
| T-6 | Maintainability | Нет Pod Disruption Budget (rolling update ронит все реплики) |
| T-7 | Масштабируемость | Нет TopologySpreadConstraints (все поды могут оказаться на одном узле) |
| T-8 | CI/CD | Нет canary-стратегии деплоя |

---

## Детальный разбор по 8 категориям

### 1. Масштабируемость

**Проблема:** Жёстко заданная 1 реплика без HPA. Синхронный I/O (psycopg2, OpenAI sync client) блокирует event loop. Celery concurrency зашит константой.

**Почему это плохо:** При LLM-запросе (200–2000ms) один поток полностью занят. При 50 RPS и concurrency=1 — очередь запросов растёт экспоненциально. Без HPA ручное масштабирование невозможно при пиковой нагрузке.

**Исправлено в patched_service:**
```yaml
# k8s/patched/deployment.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```
```python
# Было: синхронный клиент
client = OpenAI(api_key=KEY)
resp = client.chat.completions.create(...)  # blocking!

# Стало: async клиент
self._client = AsyncOpenAI(api_key=settings.openai_api_key)
resp = await self._client.chat.completions.create(...)  # non-blocking
```

---

### 2. Отказоустойчивость

**Проблема:** Нет Retry и Circuit Breaker для OpenAI API. Redis и PostgreSQL без PersistentVolumeClaim. Нет Liveness/Readiness проб. Нет Pod Disruption Budget.

**Почему это плохо:** OpenAI возвращает 429 (rate limit) в среднем 1-2 раза в час при нагрузке. Без retry — запрос падает с ошибкой. Без PVC — один `kubectl delete pod redis` = потеря всего кэша и истории. Без проб K8s не знает, что под завис, и не перезапускает его.

**Исправлено:**
```python
# patched_service/app/resilience.py
class CircuitBreaker:
    # CLOSED -> (5 failures) -> OPEN -> (60s) -> HALF_OPEN -> CLOSED

async def retry_with_backoff(func, *args, max_retries=3, base_delay=1.0, ...):
    for attempt in range(max_retries + 1):
        try:
            return await func(*args)
        except Exception:
            await asyncio.sleep(min(base_delay * 2**attempt, 30))
```
```yaml
# k8s/patched/redis.yaml — StatefulSet с PVC
volumeClaimTemplates:
  - metadata:
      name: redis-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 5Gi
```

---

### 3. Observability

**Проблема:** `print()` и запись в файл `/var/log/...`. Нет Trace-ID. Нет бизнес-метрик. PII (текст запросов) в логах.

**Почему это плохо:** Без структурированных JSON-логов невозможно настроить алерты в Grafana. Без Trace-ID при инциденте нельзя восстановить цепочку: `HTTP Request -> LLM call -> DB write`. Без метрик стоимости невозможно управлять бюджетом ($10K/месяц на LLM — реальный кейс).

**Исправлено:**
```python
# patched_service/app/observability.py
class JSONFormatter(logging.Formatter):
    def format(self, record) -> str:
        return json.dumps({
            "timestamp": ..., "level": ...,
            "trace_id": trace_id_var.get(""),  # сквозной ID
            "message": record.getMessage(),     # без PII в payload
        })

# patched_service/app/metrics.py
LLM_COST_USD = Counter("llm_cost_usd_total", "USD spent on LLM", ["model"])
LLM_TOKENS_TOTAL = Counter("llm_tokens_total", "Tokens consumed", ["type", "model"])
```

---

### 4. Безопасность

**Проблема:** API-ключи и пароли в YAML-манифестах (попадают в git). SQL-инъекция. Root в контейнерах. Нет NetworkPolicy. Внутренние ошибки клиенту.

**Почему это плохо:** Ключ в git-истории компрометируется навсегда (git filter-branch не помогает при публичном репозитории). SQL-инъекция: `'; DROP TABLE documents; --` = потеря всей базы. Root в контейнере: при RCE атакующий получает права root на хосте (если нет seccomp/AppArmor).

**Исправлено:**
```yaml
# k8s/patched/deployment.yaml
env:
  - name: OPENAI_API_KEY
    valueFrom:
      secretKeyRef:
        name: rag-secrets
        key: OPENAI_API_KEY
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]
```
```python
# Параметризованный ORM-запрос вместо f-string
await session.execute(
    insert(Document).values(content=doc.content)  # нет инъекции
)
```

---

### 5. Maintainability & DX

**Проблема:** Спагетти CI/CD без этапов. Монолитный main.py. Нет линтеров, нет тестов в пайплайне. Деплой в prod при любом push.

**Почему это плохо:** Отсутствие линтинга -> стиль расходится через 2 недели командной работы. Деплой без approval -> случайный push junior-разработчика ронит production. Без SAST-сканирования уязвимости обнаруживаются только при инциденте.

**Исправлено:** 5-stage CI/CD pipeline:
`lint -> security-scan -> build -> staging (auto) -> production (manual approval -> canary 20%)`

---

### 6. Стоимость инфраструктуры

**Проблема:** Каждый LLM-запрос идёт в OpenAI (нет кэша). TTL кэша 60 секунд. Нет учёта токенов. LoadBalancer для dev.

**Почему это плохо:** При 1000 похожих запросов/день без кэша = $50+/день дополнительных расходов. Без мониторинга стоимости: внезапный $10K счёт за месяц (реальный кейс компаний при DDoS на LLM-эндпоинт).

**Исправлено:**
```python
# patched_service/app/llm_service.py
# SHA-256 кэш с TTL=3600s (1 час)
cache_key = self._cache_key(query)
cached = await self._get_cached(cache_key)
if cached:
    # Нет запроса к OpenAI — нет затрат
    return {"response": cached, "cached": True, "cost_usd": 0.0}

# Учёт стоимости после каждого вызова
cost = in_tok * 5e-6 + out_tok * 15e-6   # gpt-4o pricing
LLM_COST_USD.labels(model=self._model).inc(cost)
```

---

### 7. Качество API и типизация

**Проблема:** `async def route(request: Request)` + `request.body()` + `json.loads()` — нет Pydantic-схем. Нет аннотаций типов.

**Почему это плохо:** Нет Swagger-документации. KeyError при любом невалидном запросе -> HTTP 500 с stack trace клиенту. mypy/pyright не работают.

**Исправлено:** Все роутеры используют `payload: QueryRequest`, `response_model=QueryResponse`.

---

### 8. Производительность

**Проблема:** Новый Redis-клиент на каждый запрос. Нет connection pool. Нет пула соединений к PostgreSQL.

**Почему это плохо:** Создание TCP-соединения к Redis: 1–5ms. При 100 RPS -> 100–500ms/sec только на handshake. PostgreSQL при лимите 100 соединений и 50 pod'ах: `too many connections` при пиковой нагрузке.

**Исправлено:**
```python
# patched_service/app/main.py — пул создаётся один раз при старте
redis_pool = aioredis.from_url(settings.redis_url)

# SQLAlchemy engine с пулом
engine = create_async_engine(url, pool_size=10, max_overflow=20)
```

---

## Production Blockers Summary

Следующие проблемы **делают невозможным** релиз в production:

1. **C-1** — Утечка секретов в git. Немедленная ротация ключей после патча.
2. **C-2** — SQL-инъекция позволяет удалить или exfiltrate всю БД.
3. **C-3** — Потеря всех данных Redis и PostgreSQL при любом rolling update или сбое узла.
4. **C-4** — Root в контейнере: полная компрометация хоста при RCE.
5. **C-5** — Без health-проб K8s не умеет self-heal: зависший под остаётся в rotation.
6. **C-6** — Redis без NetworkPolicy: любой под в namespace может прочитать весь кэш.

---

## 3-Stage Roadmap

### Этап 1 — Стабилизация и Безопасность (Week 1-2, Hotfix)

- [ ] **C-1**: Ротация ВСЕХ скомпрометированных ключей. Перевод на K8s Secrets + ESO/Vault.
- [ ] **C-2**: Замена f-string SQL на параметризованные ORM-запросы.
- [ ] **C-3**: Добавить PersistentVolumeClaim для Redis и PostgreSQL.
- [ ] **C-4**: Добавить `securityContext.runAsNonRoot: true` во все Deployments.
- [ ] **C-5**: Добавить liveness/readiness пробы.
- [ ] **C-6**: Применить NetworkPolicy для изоляции Redis и PostgreSQL.
- [ ] **M-2/M-3**: Перевод на AsyncOpenAI + asyncpg.

**Definition of Done:** Все 6 блокеров закрыты, security-scan чистый, staging не падает.

---

### Этап 2 — Наблюдаемость и Оптимизация затрат (Week 3-5, Sprint)

- [ ] **M-5/M-6**: Структурированный JSON-лог + Trace-ID через middleware.
- [ ] **M-7/M-8**: Семантический кэш (sha256 -> векторный) + метрики стоимости.
- [ ] **T-3/T-4**: Prometheus метрики + Grafana дашборд + алерт при cost > $X/day.
- [ ] **M-4**: Circuit Breaker + Retry с exponential backoff.
- [ ] **M-9/M-10/M-11**: Рефакторинг CI/CD (5-stage pipeline, SAST, approval gate).
- [ ] **T-6**: Pod Disruption Budget.

**Definition of Done:** p95 latency < 2s, cache hit > 40%, cost dashboard активен.

---

### Этап 3 — Автомасштабирование и High Availability (Week 6-8)

- [ ] **M-1**: HPA (CPU + custom metric: `llm_requests_per_second`).
- [ ] **T-7**: TopologySpreadConstraints для мульти-зонального размещения.
- [ ] **T-8**: Canary-деплой через Argo Rollouts (20% -> 50% -> 100%).
- [ ] Redis Sentinel или Cluster для HA.
- [ ] PostgreSQL с read-replica и автоматическим failover (Patroni/CloudSQL).
- [ ] KEDA для авто-скейлинга Celery-воркеров по глубине очереди Redis.
- [ ] Chaos Engineering: Chaos Mesh для проверки отказоустойчивости.

**Definition of Done:** SLA 99.9%, RTO < 5 min, RPO < 1 min, zero-downtime деплой.

---

## Матрица готовности к продакшену

| Категория | Текущий балл | Целевой балл | Статус |
|-----------|:---:|:---:|:---:|
| Масштабируемость | 1/10 | 8/10 | 🔴 Critical |
| Отказоустойчивость | 1/10 | 9/10 | 🔴 Critical |
| Observability | 2/10 | 9/10 | 🔴 Critical |
| Безопасность | 1/10 | 9/10 | 🔴 Critical |
| Maintainability | 3/10 | 8/10 | 🟠 Major |
| CI/CD | 2/10 | 9/10 | 🟠 Major |
| Стоимость | 2/10 | 8/10 | 🟠 Major |
| Производительность | 3/10 | 8/10 | 🟠 Major |
| **Общая оценка** | **1.9/10** | **8.5/10** | 🔴 **NOT READY** |

---

*Документ подготовлен в рамках архитектурного аудита. Все выявленные уязвимости подлежат
устранению до начала нагрузочного тестирования и продакшн-релиза.*
