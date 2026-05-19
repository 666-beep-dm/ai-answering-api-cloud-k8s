# MIDDLE Code Review Report: AI Service Anti-patterns → Production-Ready

> **Аудитор:** Tech Lead / AI Software Architect
> **Компонент:** FastAPI + OpenAI + PostgreSQL AI-сервис
> **Уровень:** Middle

---

## 1. Архитектура — Монолит без слоёв

### Проблема
Роутеры FastAPI напрямую инициализируют OpenAI-клиент, выполняют SQL-запросы и содержат бизнес-логику. Всё в одном файле.

### Почему это плохо
Нарушение принципов SRP и DIP: при смене LLM-провайдера придётся редактировать роутер. Юнит-тесты невозможны без поднятия реальной БД и API. Файл растёт неконтролируемо.

### Как исправить
Ввести три слоя: **Router → Service → Repository**. Каждый слой знает только о следующем.

### Сравнение

**Было (legacy_service/main.py):**
```python
@app.post("/chat")
async def chat(request: Request):
    client = OpenAI(api_key="sk-hardcoded")
    response = client.chat.completions.create(...)
    conn = psycopg2.connect(DB_URL)
    cur.execute(f"INSERT INTO messages ...")
```

**Стало (production_service/app/):**
```
routers/ai.py    → принимает HTTP, делегирует
llm_service.py   → знает об OpenAI, не знает о БД
repository.py    → знает о SQL, не знает об OpenAI
```
```python
@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, llm: LLMService = Depends(...), repo: MessageRepository = Depends(...)):
    text, tokens = await llm.chat(payload.message)
    await repo.save(payload.user_id, payload.message, text)
    return ChatResponse(response=text, tokens_used=tokens)
```

---

## 2. Разделение ответственности (SRP)

### Проблема
Функция `/chat` выполняет 5 несвязанных действий: парсинг запроса, вызов LLM, открытие соединения с БД, SQL-запрос, формирование ответа.

### Почему это плохо
При изменении любого шага нужно разбираться во всей функции. Невозможно переиспользовать логику вызова LLM в другом эндпоинте без копипасты.

### Как исправить
Каждый класс/модуль отвечает за одну ответственность. `LLMService` — только LLM, `MessageRepository` — только персистентность, роутер — только HTTP-слой.

### Сравнение

**Было:**
```python
# 50 строк всего подряд в одной функции
async def chat(request: Request):
    data = await request.json()
    client = OpenAI(...)
    response = client.chat.completions.create(...)
    conn = psycopg2.connect(...)
    cur.execute(...)
    return {"response": ...}
```

**Стало:**
```python
# LLMService: только LLM
async def chat(self, message: str) -> tuple[str, int]: ...

# MessageRepository: только БД
async def save(self, user_id: int, message: str, response: str) -> Message: ...

# Router: только HTTP
async def chat(payload: ChatRequest, llm=Depends(...), repo=Depends(...)): ...
```

---

## 3. Безопасность — Захардкоженный ключ и SQL-инъекции

### Проблема
API-ключ OpenAI зашит в код (`sk-hardcoded-key-...`). SQL-запросы строятся через f-string с пользовательскими данными.

### Почему это плохо
Ключ попадёт в git-историю навсегда. SQL-инъекция позволяет злоумышленнику выполнить произвольный SQL: `user_id = 1 OR 1=1 --` вернёт все записи; `'; DROP TABLE messages; --` удалит таблицу.

### Как исправить
Ключи — в `.env`, читать через `pydantic-settings`. SQL — только через параметризованные запросы ORM.

### Сравнение

**Было:**
```python
OPENAI_KEY = "sk-hardcoded-key-1234567890abcdef"  # в git!

cur.execute(
    f"SELECT * FROM messages WHERE user_id = {user_id}"  # injection!
)
```

**Стало:**
```python
# .env (не в git)
OPENAI_API_KEY=sk-real-key-from-env

# config.py
class Settings(BaseSettings):
    openai_api_key: str  # читается из .env, валидируется Pydantic

# repository.py — параметризованный ORM-запрос
result = await self._session.execute(
    select(Message).where(Message.user_id == user_id)
)
```

---

## 4. Логирование — print() и утечка чувствительных данных

### Проблема
Используется `print()` для логирования. В логи попадают: сообщения пользователей (PII), содержимое LLM-ответов, OpenAI API-ключ.

### Почему это плохо
`print()` не поддерживает уровни, ротацию, структурированный формат. PII в логах нарушает GDPR/152-ФЗ. API-ключ в stdout виден в docker logs любому, у кого есть доступ к хосту.

### Как исправить
Использовать `logging` с конфигурацией через `logging.config.dictConfig`. Никогда не логировать содержимое пользовательских сообщений и секреты.

### Сравнение

**Было:**
```python
print(f"[INFO] user_id={user_id} message={user_message}")  # PII!
print(f"[DEBUG] Using API key: {OPENAI_KEY}")               # секрет в stdout!
```

**Стало:**
```python
# main.py — структурированная конфигурация
logging.config.dictConfig(LOGGING_CONFIG)

# llm_service.py — только метаданные, без содержимого
logger.info("LLM chat request, model=%s", self._model)
logger.debug("LLM chat completed, tokens=%d", tokens)

# config.py — маскирование ключа
def masked_openai_key(self) -> str:
    k = self.openai_api_key
    return f"{k[:6]}...{k[-4:]}"
```

---

## 5. Управление окружением (ENV) — os.environ без валидации

### Проблема
Конфигурация читается через `os.environ.get("DATABASE_URL")` без значения по умолчанию, без типизации, без проверки наличия.

### Почему это плохо
Если переменная не задана, `DATABASE_URL` будет `None`, и psycopg2 упадёт с `TypeError` при первом запросе — не при старте. Нет единого места, где видны все требуемые переменные.

### Как исправить
`pydantic-settings` валидирует все переменные при старте приложения: если чего-то нет — `ValidationError` сразу, до первого запроса.

### Сравнение

**Было:**
```python
DB_URL = os.environ.get("DATABASE_URL")  # None если не задано
OPENAI_KEY = "sk-hardcoded"              # захардкожен
```

**Стало:**
```python
class Settings(BaseSettings):
    openai_api_key: str          # обязательное поле — ошибка при старте, если нет
    database_url: str            # обязательное поле
    openai_model: str = "gpt-4o" # опциональное с дефолтом
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env")
```

---

## 6. Async/Sync — Блокировка Event Loop

### Проблема
В `async def` хэндлерах используются синхронный `OpenAI()` клиент и синхронный драйвер `psycopg2`. Обе операции блокируют event loop.

### Почему это плохо
FastAPI основан на asyncio. Синхронный I/O внутри `async def` означает: пока выполняется запрос к OpenAI (200-2000 мс) или к PostgreSQL, **все остальные запросы к сервису стоят в очереди**. При 10 RPS деградация производительности становится катастрофической.

### Как исправить
`AsyncOpenAI` для LLM, `asyncpg` через `SQLAlchemy[asyncio]` для БД.

### Сравнение

**Было:**
```python
# Блокирует event loop на 200-2000ms!
client = OpenAI(api_key=OPENAI_KEY)           # синхронный
response = client.chat.completions.create(...) # blocking I/O

conn = psycopg2.connect(DB_URL)               # синхронный
cur.execute(...)                               # blocking I/O
```

**Стало:**
```python
# Не блокирует — event loop свободен
self._client = AsyncOpenAI(api_key=settings.openai_api_key)
resp = await self._client.chat.completions.create(...)  # async

# SQLAlchemy 2.0 async через asyncpg
engine = create_async_engine(settings.database_url)
async with AsyncSessionLocal() as session:
    await session.execute(select(Message).where(...))  # async
```

---

## 7. Качество API — Отсутствие Pydantic-схем

### Проблема
Все эндпоинты принимают `Request` и читают тело через `request.json()`, возвращают сырые `dict`.

### Почему это плохо
FastAPI не генерирует Swagger-документацию. Любой невалидный payload (отсутствующее поле, неверный тип) вызывает необработанный `KeyError` с кодом 500. Нет контракта API — фронтенд-команда не знает, что ожидать.

### Как исправить
Все входные данные — через Pydantic `BaseModel`. Все ответы — через `response_model=...`.

### Сравнение

**Было:**
```python
@app.post("/chat")
async def chat(request: Request):
    data = await request.json()          # KeyError если нет поля
    user_id = data["user_id"]
    return {"response": ai_text}         # нет схемы → нет Swagger
```

**Стало:**
```python
class ChatRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    message: str = Field(..., min_length=1, max_length=4096)

class ChatResponse(BaseModel):
    response: str
    tokens_used: int

@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, ...) -> ChatResponse:
    ...  # автовалидация + полная Swagger-документация
```

---

## 8. Типизация — Полное отсутствие Type Hints

### Проблема
Ни одна функция не имеет аннотаций типов ни для параметров, ни для возвращаемых значений.

### Почему это плохо
IDE не может выдать подсказки. `mypy`/`pyright` не работают. При рефакторинге ошибки несоответствия типов обнаруживаются только в production. Онбординг новых разработчиков занимает в 2–3 раза больше времени.

### Как исправить
Аннотировать все функции, использовать `from __future__ import annotations` для Python < 3.10.

### Сравнение

**Было:**
```python
async def chat(request):           # что принимает? что возвращает?
    data = await request.json()    # dict? что внутри?
    client = OpenAI(...)
    return {"response": ai_text}   # какой тип у ai_text?
```

**Стало:**
```python
async def chat(
    payload: ChatRequest,
    llm: LLMService = Depends(get_llm_service),
    repo: MessageRepository = Depends(get_message_repo),
) -> ChatResponse:
    text, tokens = await llm.chat(payload.message)  # tuple[str, int]
    return ChatResponse(response=text, tokens_used=tokens)
```

---

## 9. Производительность — N+1 соединений с БД

### Проблема
Каждый HTTP-запрос открывает новое соединение к PostgreSQL (`psycopg2.connect(...)`) и закрывает его в конце хэндлера.

### Почему это плохо
Установка TCP-соединения + PostgreSQL handshake занимает 5–50 мс. При 100 RPS сервис тратит 500–5000 мс/сек только на установку соединений. PostgreSQL имеет лимит соединений (по умолчанию 100) — при пиковой нагрузке сервис упадёт с `too many connections`.

### Как исправить
Connection Pool через `SQLAlchemy create_async_engine` с `pool_size` и `max_overflow`. Соединения переиспользуются между запросами.

### Сравнение

**Было:**
```python
# Каждый запрос: открыть → использовать → закрыть
conn = psycopg2.connect(DB_URL)  # 5-50ms на handshake
cur = conn.cursor()
cur.execute(...)
conn.commit()
conn.close()  # соединение уничтожено
```

**Стало:**
```python
# Один раз при старте — пул на весь lifetime приложения
engine = create_async_engine(
    settings.database_url,
    pool_size=10,      # 10 постоянных соединений
    max_overflow=20,   # до 30 при пике
    pool_pre_ping=True # проверка живости соединения
)

# FastAPI dependency — берёт соединение из пула (< 1ms)
async with AsyncSessionLocal() as session:
    await session.execute(...)
# соединение возвращается в пул, не уничтожается
```

---

## Итоговая матрица

| # | Категория | Severity | Статус |
|---|-----------|----------|--------|
| 1 | Архитектура | 🔴 Critical | ✅ Исправлено |
| 2 | SRP | 🔴 Critical | ✅ Исправлено |
| 3 | Безопасность | 🔴 Critical | ✅ Исправлено |
| 4 | Логирование / PII | 🟠 High | ✅ Исправлено |
| 5 | ENV / Конфигурация | 🟠 High | ✅ Исправлено |
| 6 | Async/Sync блокировка | 🔴 Critical | ✅ Исправлено |
| 7 | Качество API | 🟠 High | ✅ Исправлено |
| 8 | Типизация | 🟡 Medium | ✅ Исправлено |
| 9 | Производительность (N+1) | 🔴 Critical | ✅ Исправлено |
