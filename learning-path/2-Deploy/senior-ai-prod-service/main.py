import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.db import init_db
from src.cache import close_redis
from src.logging_config import configure_logging
from src.metrics import metrics_endpoint
from src.rag.retriever import load_vectorstore
from src.api.ask import router as ask_router
from src.api.health import router as health_router
from src.api.history import router as history_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    configure_logging(s.log_level)
    log = logging.getLogger(__name__)
    log.info("🚀 Starting %s [%s]", s.app_name, s.app_env)

    await init_db()
    log.info("✅ Database initialised")

    await load_vectorstore()
    log.info("✅ Vector store loaded")

    yield

    await close_redis()
    log.info("🛑 Service shut down cleanly")


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title=s.app_name,
        version=s.app_version,
        description="Production RAG service — FastAPI + LangChain + PostgreSQL + Redis",
        docs_url="/docs" if s.app_env != "production" else None,
        redoc_url="/redoc" if s.app_env != "production" else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if s.debug else ["https://yourdomain.com"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(ask_router, prefix="/api/v1")
    app.include_router(health_router)
    app.include_router(history_router, prefix="/api/v1")

    if s.metrics_enabled:
        app.get("/metrics", include_in_schema=False)(metrics_endpoint)

    @app.exception_handler(Exception)
    async def _global_exc(request: Request, exc: Exception):
        logging.getLogger(__name__).exception("unhandled_error")
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )

    return app


app = create_app()
