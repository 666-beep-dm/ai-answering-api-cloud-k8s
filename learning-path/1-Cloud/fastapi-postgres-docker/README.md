# FastAPI + PostgreSQL · Docker · Cloud-Ready

> **Production-grade** REST API сервис с PostgreSQL, оптимизированным multi-stage Docker-образом и полным гайдом по деплою на AWS EC2 / GCP Compute Engine.

---

## Содержание

1. [Стек технологий](#стек)
2. [Быстрый старт локально](#быстрый-старт)
3. [Структура проекта](#структура)
4. [Переменные окружения](#переменные-окружения)
5. [Деплой на облачную VM](#деплой-на-облачную-vm)
6. [Firewall / Security Groups](#firewall--security-groups)
7. [Установка Docker на Ubuntu 22.04](#установка-docker)
8. [Мониторинг и отладка](#мониторинг)
9. [API Reference](#api-reference)

---

## Стек

| Компонент | Технология |
|-----------|-----------|
| Web framework | FastAPI 0.111 + Uvicorn |
| Database | PostgreSQL 15 (Alpine) |
| ORM | SQLAlchemy 2.0 (async) + asyncpg |
| Контейнеризация | Docker 24+ / Docker Compose v2 |
| Python | 3.11 (slim, multi-stage build) |

---

## Быстрый старт

```bash
# 1. Клонировать / разархивировать проект
cd fastapi-postgres-docker

# 2. Создать .env из шаблона и задать пароль
cp .env.example .env
# Отредактируй .env — смени POSTGRES_PASSWORD!

# 3. Запустить
docker compose up -d

# 4. Проверить
curl http://localhost:8000/
curl http://localhost:8000/health
```

---

## Структура проекта

```
fastapi-postgres-docker/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI — роуты / и /health
│   └── database.py      # SQLAlchemy async engine + health probe
├── scripts/
│   └── wait-for-db.sh   # TCP-поллинг перед стартом приложения
├── nginx/               # (опционально) reverse-proxy конфиги
├── Dockerfile           # Multi-stage: builder → runtime
├── docker-compose.yml   # Сервисы: app + db + сети + volumes
├── requirements.txt
├── .env.example         # Шаблон переменных окружения
├── .gitignore
└── README.md
```

---

## Переменные окружения

Скопируй `.env.example` → `.env` и заполни:

| Переменная | Описание | Пример |
|------------|----------|--------|
| `APP_NAME` | Имя сервиса | `fastapi-postgres` |
| `APP_ENV` | Среда запуска | `production` |
| `POSTGRES_USER` | Пользователь БД | `appuser` |
| `POSTGRES_PASSWORD` | **Пароль БД** (обязательно сменить!) | `str0ng_p@ss` |
| `POSTGRES_DB` | Имя базы данных | `appdb` |

> ⚠️ **Никогда не коммить `.env` в Git.** Он добавлен в `.gitignore`.

---

## Деплой на облачную VM

### Шаг 1 — Подключиться к серверу

```bash
# AWS
ssh -i ~/.ssh/your-key.pem ubuntu@<EXTERNAL_IP>

# GCP (через gcloud)
gcloud compute ssh your-vm-name --zone=us-central1-a
```

### Шаг 2 — Установить Docker (одна команда)

```bash
curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker $USER && newgrp docker
```

Проверка:
```bash
docker --version && docker compose version
```

### Шаг 3 — Деплой приложения

```bash
git clone https://github.com/ВАШ_НИК/fastapi-postgres-docker.git
cd fastapi-postgres-docker
cp .env.example .env
nano .env          # ← сменить POSTGRES_PASSWORD!
docker compose up -d
```

---

## Firewall / Security Groups

Открой только необходимые порты:

| Порт | Протокол | Источник | Назначение |
|------|----------|----------|-----------|
| **22** | TCP | Ваш IP | SSH доступ |
| **8000** | TCP | 0.0.0.0/0 | FastAPI API |
| 5432 | TCP | ❌ закрыт | PostgreSQL — только внутри Docker сети |

### AWS — Security Group (Inbound rules)

1. EC2 → **Security Groups** → твоя группа → **Edit inbound rules**
2. Добавь два правила:

```
Type: Custom TCP | Port: 8000 | Source: 0.0.0.0/0   | Description: FastAPI
Type: SSH        | Port: 22   | Source: <YOUR_IP>/32  | Description: SSH admin
```

3. **Save rules**

### GCP — VPC Firewall Rules

```bash
# Открыть порт 8000
gcloud compute firewall-rules create allow-fastapi \
  --allow tcp:8000 \
  --source-ranges 0.0.0.0/0 \
  --description "FastAPI app port"

# SSH (порт 22) уже открыт по умолчанию
```

---

## Установка Docker

**Одной командой на Ubuntu 22.04:**

```bash
curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker $USER && newgrp docker
```

Эта команда:
- Скачивает и запускает официальный install-скрипт Docker
- Добавляет текущего пользователя в группу `docker`
- Применяет членство в группе без перелогина

---

## Мониторинг

### Статус контейнеров

```bash
docker compose ps
```

### Healthcheck статус

```bash
docker inspect fastapi_app | grep -A 10 '"Health"'
docker inspect pg_db      | grep -A 10 '"Health"'
```

### Логи в реальном времени

```bash
docker compose logs -f          # все сервисы
docker compose logs -f app      # только FastAPI
docker compose logs -f db       # только PostgreSQL
```

### Перезапуск / обновление

```bash
git pull
docker compose up -d --build    # пересобрать образ и перезапустить
```

### Остановить всё

```bash
docker compose down             # остановить (данные сохранятся в volume)
docker compose down -v          # ⚠️ удалить вместе с данными БД
```

---

## API Reference

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/` | Статус сервиса |
| GET | `/health` | Healthcheck + проверка соединения с БД |
| GET | `/docs` | Swagger UI (автогенерация) |
| GET | `/redoc` | ReDoc документация |

### Пример ответа `/health` (200 OK)

```json
{
  "status": "healthy",
  "database": {
    "connected": true,
    "detail": "ok"
  }
}
```

### Пример ответа `/health` при недоступной БД (503)

```json
{
  "status": "unhealthy",
  "database": {
    "connected": false,
    "detail": "could not connect to server: Connection refused"
  }
}
```
