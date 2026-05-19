"""production_service/app/main.py — точка входа, настройка приложения."""

import logging
import logging.config
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .config import get_settings
from .database import engine, Base
from .routers import ai

# ─── Структурированное логирование ───────────────────────────────────────────
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(
        "Starting %s v%s | OpenAI key: %s",
        settings.app_title,
        settings.app_version,
        settings.masked_openai_key(),   # ключ замаскирован!
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    logger.info("Shutting down")
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.include_router(ai.router)
    return app


app = create_app()
