import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from database import init_db
from app.api.items import router as items_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("⚙️  Initialising database …")
    await init_db()
    logger.info("✅ Database ready")
    yield
    logger.info("🛑 Shutting down")


app = FastAPI(
    title="Middle-tier CRUD Service",
    version="1.0.0",
    description="FastAPI + PostgreSQL + Nginx — production-ready scaffold",
    lifespan=lifespan,
)

app.include_router(items_router, prefix="/api/v1")


@app.get("/health", tags=["Ops"])
async def health():
    return {"status": "ok"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
