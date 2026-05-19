# 🐛 FastAPI 500-Error Debug Stand

Учебный стенд для Junior-разработчиков: воспроизведение, логирование и исправление
`500 Internal Server Error` на реальном FastAPI-проекте.

---

## System Requirements

| Параметр | Минимум | Рекомендуется |
|----------|---------|---------------|
| RAM      | 4 GB    | 16 GB         |
| CPU      | 2 cores | 4 cores       |
| Docker   | 24+     | latest        |
| Python   | 3.10+   | 3.11+         |

---

## Структура проекта

```
junior_debug_project/
├── app/
│   ├── __init__.py
│   └── main.py          # FastAPI: баг + фикс + логирование
├── tests/
│   └── test_users.py    # Pytest-тесты для обоих режимов
├── .env.example         # Шаблон переменных окружения
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Шаг 0 — Подготовка окружения (Git Bash / Terminal)

```bash
# Перейдите в папку проекта
cd junior_debug_project

# Создайте .env из шаблона
cp .env.example .env
```

---

## Шаг 1 — Воспроизвести ошибку 500 (BUG MODE)

В `.env` должно быть `BUG_MODE=true` (установлено по умолчанию).

```bash
# Соберите образ и запустите контейнер
docker-compose up --build
```

В новом терминале:

```bash
# Вариант A — через curl
curl -s http://localhost:8000/users | python -m json.tool

# Вариант B — откройте Swagger UI в браузере
# http://localhost:8000/docs  →  GET /users  →  Try it out  →  Execute
```

**Ожидаемый ответ:**
```json
{
  "error": "KeyError",
  "detail": "\'email\'",
  "hint": "Check server logs for the full traceback."
}
```

**Логи в консоли (уровень ERROR):**
```
2024-01-15T10:23:01 | ERROR    | debug_stand | KeyError in GET /users | missing_key='email' | bug_mode=True
2024-01-15T10:23:01 | ERROR    | debug_stand | Unhandled exception | error_type=KeyError | method=GET | path=/users
```

---

## Шаг 2 — Переключить на исправленную версию (FIX MODE)

```bash
# Остановите контейнер (Ctrl+C или отдельный терминал)
docker-compose down

# Измените .env
# BUG_MODE=false

# Пересоберите и запустите
docker-compose up --build
```

```bash
# Проверьте исправленный эндпоинт
curl -s http://localhost:8000/users | python -m json.tool
```

**Ожидаемый ответ:**
```json
{
  "users": [
    {"id": 1, "name": "Alice",   "email": "alice@example.com"},
    {"id": 2, "name": "Bob",     "email": "bob@example.com"},
    {"id": 3, "name": "Charlie", "email": "charlie@example.com"}
  ],
  "count": 3
}
```

**Логи (уровень INFO):**
```
2024-01-15T10:25:03 | INFO     | debug_stand | GET /users called | bug_mode=False
2024-01-15T10:25:03 | INFO     | debug_stand | GET /users success | returned 3 users
```

---

## Шаг 3 — Запустить тесты

```bash
# Установите зависимости локально (вне Docker)
pip install -r requirements.txt

# Запустите тесты
pytest tests/ -v
```

---

## Шаг 4 — Зафиксировать результат в Git

```bash
git init
git add .
git commit -m "fix: resolve 500 error on /users endpoint and add logging"
```

---

## Разбор бага

### Что пошло не так?

В `FAKE_DB_BUGGY` второй пользователь не содержит ключ `"email"`:

```python
{"id": 2, "name": "Bob"}   # KeyError: 'email'
```

Прямое обращение `user["email"]` в `_process_users_buggy()` бросает `KeyError`.

### Как исправлено?

Метод `.get()` с fallback-значением:

```python
"email": user.get("email", "no-email@example.com")
```

И данные в `FAKE_DB_FIXED` содержат все обязательные поля.

### Почему важно логирование?

Без `logger.error(..., exc_info=True)` traceback теряется, и причину 500-ки
найти в продакшене крайне сложно. Уровни:
- `INFO`  — успешные запросы, старт/стоп сервиса
- `ERROR` — исключения с полным traceback

---

## Полезные команды

```bash
# Логи контейнера в реальном времени
docker-compose logs -f

# Остановить и удалить контейнер
docker-compose down

# Пересобрать без кеша
docker-compose build --no-cache
```
