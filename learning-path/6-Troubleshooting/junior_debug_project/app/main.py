"""
FastAPI Debug Training Stand
==============================
Цель: показать Junior-разработчику, как воспроизвести 500-ку,
      правильно её поймать, залогировать и исправить.

Переключение режимов
--------------------
  BUG_MODE=True   → эндпоинт GET /users бросает 500 (KeyError)
  BUG_MODE=False  → рабочий, исправленный вариант

Управление через .env:
  BUG_MODE=true   docker-compose up --build
  BUG_MODE=false  docker-compose up --build
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ── Logging setup ──────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("debug_stand")

# ── Config ─────────────────────────────────────────────────────────────
BUG_MODE: bool = os.getenv("BUG_MODE", "true").lower() in ("1", "true", "yes")

# ── Fake "database" ────────────────────────────────────────────────────
# Намеренно отсутствует ключ "email" у второго пользователя — классический KeyError.
FAKE_DB_BUGGY = [
    {"id": 1, "name": "Alice", "email": "alice@example.com"},
    {"id": 2, "name": "Bob"},          # <-- KeyError: 'email'
    {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
]

# Исправленная версия: все поля присутствуют + используем .get() с дефолтом.
FAKE_DB_FIXED = [
    {"id": 1, "name": "Alice",   "email": "alice@example.com"},
    {"id": 2, "name": "Bob",     "email": "bob@example.com"},
    {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
]


# ── Application factory ────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    mode = "BUG" if BUG_MODE else "FIXED"
    logger.info("🚀 App started | mode=%s | log_level=%s", mode, LOG_LEVEL)
    yield
    logger.info("🛑 App shutting down")


app = FastAPI(
    title="500-Error Debug Stand",
    description="Учебный стенд: воспроизведение и исправление 500 Internal Server Error",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Global Exception Handler ───────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Перехватывает все необработанные исключения.
    Логирует: тип ошибки, сообщение, метод и путь запроса.
    """
    logger.error(
        "Unhandled exception | error_type=%s | message=%s | method=%s | path=%s",
        type(exc).__name__,
        str(exc),
        request.method,
        request.url.path,
        exc_info=True,          # добавляет полный traceback в лог
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": type(exc).__name__,
            "detail": str(exc),
            "hint": "Check server logs for the full traceback.",
        },
    )


# ── Helper: buggy data processing ─────────────────────────────────────
async def _process_users_buggy(users: list) -> list:
    """
    ❌ BUGGY VERSION
    Прямое обращение user["email"] без проверки существования ключа.
    Если у хотя бы одного пользователя нет поля email — KeyError → 500.
    """
    result = []
    for user in users:
        result.append({
            "id":    user["id"],
            "name":  user["name"],
            "email": user["email"],   # <-- KeyError здесь, если ключ отсутствует
        })
    return result


async def _process_users_fixed(users: list) -> list:
    """
    ✅ FIXED VERSION
    Используем .get() с дефолтным значением — никаких KeyError.
    Pydantic-модели (см. schemas.py) добавят валидацию на уровне типов.
    """
    result = []
    for user in users:
        result.append({
            "id":    user.get("id"),
            "name":  user.get("name", "Unknown"),
            "email": user.get("email", "no-email@example.com"),
        })
    return result


# ── Endpoints ──────────────────────────────────────────────────────────
@app.get("/users", tags=["users"], summary="Get all users")
async def get_users():
    """
    Возвращает список пользователей.

    * **BUG_MODE=true**  → KeyError → 500 Internal Server Error
    * **BUG_MODE=false** → корректный список пользователей
    """
    logger.info("GET /users called | bug_mode=%s", BUG_MODE)

    try:
        if BUG_MODE:
            # ─────────────────────────────────────────────────────────
            # ❌ BUGGY CODE (намеренная ошибка для демонстрации)
            # ─────────────────────────────────────────────────────────
            users = await _process_users_buggy(FAKE_DB_BUGGY)
        else:
            # ─────────────────────────────────────────────────────────
            # ✅ FIXED CODE
            # ─────────────────────────────────────────────────────────
            users = await _process_users_fixed(FAKE_DB_FIXED)

        logger.info("GET /users success | returned %d users", len(users))
        return {"users": users, "count": len(users)}

    except KeyError as exc:
        # Локальный перехват — логируем с уровнем ERROR и пробрасываем дальше,
        # чтобы global_exception_handler вернул клиенту стандартный 500-ответ.
        logger.error(
            "KeyError in GET /users | missing_key=%s | bug_mode=%s",
            str(exc), BUG_MODE,
            exc_info=True,
        )
        raise  # пробрасываем в global_exception_handler


@app.get("/health", tags=["meta"], summary="Health check")
async def health_check():
    logger.info("GET /health called")
    return {"status": "ok", "bug_mode": BUG_MODE}
