# Junior Code Review Stand 🔍

Учебный стенд для проведения Code Review FastAPI CRUD-приложения (users + tasks).

---

## System Requirements

| Параметр | Рекомендуемое значение |
|----------|------------------------|
| ОС       | Windows 10/11, macOS 12+, Ubuntu 22.04 |
| RAM      | **16 GB** |
| CPU      | **4 ядра** |
| Python   | 3.10+ |
| Docker   | 24+ |
| Git Bash | Последняя версия (Windows) |

---

## Структура проекта

```
junior_code_review_project/
├── legacy_app/         ← «Грязный» код с 10 ошибками
│   ├── main.py
│   └── requirements.txt
├── prod_app/           ← Чистая, рефакторенная версия
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── schemas.py
│   ├── models.py
│   ├── requirements.txt
│   └── routers/
│       ├── __init__.py
│       ├── users.py
│       └── tasks.py
├── docs/
│   └── CODE_REVIEW.md  ← Отчёт с разбором всех 10 ошибок
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## Шаг 1 — Анализ Legacy-кода (Git Bash)

```bash
# Откройте Git Bash и перейдите в папку проекта
cd junior_code_review_project

# Посмотрите «грязный» код
cat legacy_app/main.py

# Прочитайте отчёт Code Review
cat docs/CODE_REVIEW.md

# Сравните с рефакторенной версией
cat prod_app/routers/users.py
```

---

## Шаг 2 — Запуск исправленного приложения через Docker

```bash
# Скопируйте .env.example в .env
cp .env.example .env

# Соберите и запустите контейнер
docker-compose up --build

# Откройте Swagger UI в браузере:
# http://localhost:8000/docs

# Остановить:
docker-compose down
```

---

## Шаг 3 — Локальный запуск без Docker (опционально)

```bash
cd junior_code_review_project

# Создайте виртуальное окружение
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
# или: source .venv/bin/activate  # macOS/Linux

# Установите зависимости
pip install -r prod_app/requirements.txt

# Запустите
uvicorn prod_app.main:app --reload --port 8000
```

---

## Шаг 4 — Публикация на GitHub (Git Bash)

```bash
# Инициализируйте репозиторий
git init

# Добавьте все файлы
git add .

# Создайте первый коммит
git commit -m "chore: add code review stand with legacy and refactored apps"

# Добавьте remote (замените YOUR_USERNAME и YOUR_REPO)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git

# Отправьте на GitHub
git branch -M main
git push -u origin main
```

---

## API Endpoints (prod_app)

### Users
| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/users/` | Список пользователей |
| POST | `/users/` | Создать пользователя |
| GET | `/users/{id}` | Получить пользователя |
| DELETE | `/users/{id}` | Удалить пользователя |

### Tasks
| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/tasks/` | Список задач |
| POST | `/tasks/` | Создать задачу |
| GET | `/tasks/{id}` | Получить задачу |
| DELETE | `/tasks/{id}` | Удалить задачу |

---

## Полезные ссылки

- 📖 [PEP8 — Руководство по стилю Python](https://pep8.org)
- 📖 [FastAPI Docs](https://fastapi.tiangolo.com)
- 📖 [Pydantic V2](https://docs.pydantic.dev)
- 📖 [aiosqlite](https://aiosqlite.omnilib.dev)
