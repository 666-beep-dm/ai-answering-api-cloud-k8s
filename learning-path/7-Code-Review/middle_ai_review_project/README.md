# Middle AI Code Review Stand 🤖

Учебный стенд для Code Review уровня **Middle**: FastAPI + OpenAI + PostgreSQL.
Демонстрирует 9 критических архитектурных и инфраструктурных антипаттернов
и их production-ready решения.

---

## Recommended Hardware

| Параметр | Минимум | Рекомендуется |
|----------|---------|---------------|
| RAM | 8 GB | **16 GB** |
| CPU | 2 ядра | **4 ядра** |
| Disk | 10 GB | 20 GB SSD |
| OS | Ubuntu 20.04 / macOS 12 / Windows 10 | Latest |
| Docker | 24+ | Latest |
| Python | 3.10+ | 3.12 |

---

## Структура проекта

```
middle_ai_review_project/
├── legacy_service/
│   ├── main.py             ← монолит с 9 антипаттернами
│   └── requirements.txt
├── production_service/
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py         ← точка входа, настройка logging/lifespan
│       ├── config.py       ← pydantic-settings
│       ├── database.py     ← async engine + session factory
│       ├── models.py       ← SQLAlchemy ORM модели
│       ├── schemas.py      ← Pydantic Request/Response схемы
│       ├── repository.py   ← слой работы с БД
│       ├── llm_service.py  ← слой работы с OpenAI
│       ├── dependencies.py ← FastAPI DI + auth
│       └── routers/
│           └── ai.py       ← тонкий HTTP-роутер
├── docs/
│   └── MIDDLE_CODE_REVIEW.md
├── Dockerfile              ← multi-stage build
├── docker-compose.yml      ← API + PostgreSQL с изоляцией
├── .env.example
├── .gitignore
└── README.md
```

---

## Шаг 1 — Анализ Legacy-кода

```bash
# Git Bash
cd middle_ai_review_project

# Изучите антипаттерны с комментариями #! ARCH #! SEC #! ASYNC ...
cat legacy_service/main.py

# Прочитайте детальный код-ревью отчёт
cat docs/MIDDLE_CODE_REVIEW.md
```

---

## Шаг 2 — Запуск Production-сервиса

```bash
# Скопируйте и заполните .env
cp .env.example .env
# Откройте .env и укажите OPENAI_API_KEY и API_TOKEN_SECRET

# Сборка и запуск в фоне
docker-compose up --build -d

# Проверить статус
docker-compose ps

# Swagger UI
# http://localhost:8000/docs

# Логи
docker-compose logs -f api

# Остановить
docker-compose down
```

---

## Шаг 3 — Тестирование API

```bash
# Создать сообщение (нужен X-API-Token из .env API_TOKEN_SECRET)
curl -X POST http://localhost:8000/ai/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Token: your_secret" \
  -d '{"user_id": 1, "message": "Hello, GPT!"}'

# История сообщений
curl http://localhost:8000/ai/history?user_id=1 \
  -H "X-API-Token: your_secret"

# Суммаризация
curl -X POST http://localhost:8000/ai/summarize \
  -H "Content-Type: application/json" \
  -H "X-API-Token: your_secret" \
  -d '{"text": "Long text to summarize..."}'
```

---

## Шаг 4 — Публикация на GitHub (Git Bash)

```bash
git init
git add .
git commit -m "feat: complete middle code review and refactoring of AI service"

# Замените YOUR_USERNAME / YOUR_REPO
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

---

## Архитектурная диаграмма (Production)

```
HTTP Request
    │
    ▼
┌─────────────────────┐
│   routers/ai.py     │  ← только HTTP, Pydantic схемы, DI
└────────┬────────────┘
         │ Depends()
    ┌────┴────────┐
    │             │
    ▼             ▼
┌──────────┐  ┌────────────────┐
│LLMService│  │MessageRepository│  ← разные ответственности
│AsyncOpenAI│  │AsyncSession    │
└──────────┘  └───────┬────────┘
                      │
                      ▼
               ┌─────────────┐
               │ PostgreSQL  │  ← изолирован в Docker network
               └─────────────┘
```

---

## Полезные ссылки

- [FastAPI Docs](https://fastapi.tiangolo.com)
- [Pydantic-Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [SQLAlchemy 2.0 Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [AsyncOpenAI](https://github.com/openai/openai-python#async-usage)
- [OWASP SQL Injection](https://owasp.org/www-community/attacks/SQL_Injection)
