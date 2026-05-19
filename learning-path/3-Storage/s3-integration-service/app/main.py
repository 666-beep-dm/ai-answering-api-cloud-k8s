from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.logging import setup_logging

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    yield
    # shutdown (aioboto3 sessions clean up automatically)


app = FastAPI(
    title="S3 Integration Service",
    description=(
        "Async microservice for uploading files and generating presigned URLs "
        "for any S3-compatible object storage (AWS S3, Selectel, MinIO)."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/health", tags=["system"], summary="Health check")
async def health() -> dict:
    return {"status": "ok", "service": "s3-integration-service"}
