# AI Answering API

Минималистичный, production-ready FastAPI сервис, отвечающий на вопросы через **GPT-4o-mini**.

---

## Системные требования

| Ресурс | Минимум    |
|--------|------------|
| RAM    | 16 GB      |
| CPU    | 4 ядра     |
| Docker | 24+        |
| Git    | любой      |

---

## Структура проекта

```
junior_ai_api/
├── app/
│   ├── __init__.py
│   ├── main.py        ← FastAPI приложение, middleware, endpoint
│   └── schemas.py     ← Pydantic v2 схемы
├── config/
│   ├── __init__.py
│   └── settings.py    ← Конфигурация через pydantic-settings
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Быстрый старт (Git Bash)

### 1. Настройка окружения

```bash
cp .env.example .env
# Открой .env и вставь свой OPENAI_API_KEY
# Для работы без ключа установи: USE_MOCK=true
```

### 2. Инициализация Git-репозитория

```bash
git init
git add .
git commit -m "feat: initial AI Answering API setup"
```

### 3. Сборка и запуск через Docker

```bash
docker-compose up --build -d
```

Сервис будет доступен на **http://localhost:8000**

### 4. Проверка эндпоинта через curl

```bash
curl -X POST http://localhost:8000/ask \
     -H "Content-Type: application/json" \
     -d "{\"question\": \"Что такое искусственный интеллект?\"}"
```

Ожидаемый ответ:
```json
{"answer": "Искусственный интеллект — это..."}
```

### 5. Проверка обработки ошибок (пустой вопрос → 400)

```bash
curl -X POST http://localhost:8000/ask \
     -H "Content-Type: application/json" \
     -d "{\"question\": \"   \"}"
```

### 6. Swagger UI

Открой в браузере: **http://localhost:8000/docs**

### 7. Остановка сервиса

```bash
docker-compose down
```

---

## Переменные окружения

| Переменная       | По умолчанию   | Описание                                  |
|------------------|----------------|-------------------------------------------|
| `OPENAI_API_KEY` | —              | Ключ OpenAI API                           |
| `OPENAI_MODEL`   | `gpt-4o-mini`  | Модель для генерации ответов              |
| `USE_MOCK`       | `false`        | `true` — заглушка без реального API       |
| `LOG_LEVEL`      | `INFO`         | Уровень логирования                       |

---

## Публикация на GitHub

```bash
git remote add origin https://github.com/<ваш-логин>/<репозиторий>.git
git branch -M main
git push -u origin main
```

---

## API Reference

### `POST /ask`

**Тело запроса:**
```json
{ "question": "Ваш вопрос здесь" }
```

**Успешный ответ (200):**
```json
{ "answer": "Ответ от модели" }
```

**Ошибка валидации (400/422):**
```json
{ "detail": [{"msg": "Question must not be blank..."}] }
```

**Ошибка LLM (500):**
```json
{ "detail": "LLM service error: ..." }
```
