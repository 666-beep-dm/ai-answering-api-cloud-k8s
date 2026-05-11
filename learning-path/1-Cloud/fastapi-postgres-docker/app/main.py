from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.database import check_db_connection
import os

app = FastAPI(
    title="FastAPI + PostgreSQL",
    description="Production-ready FastAPI service with PostgreSQL",
    version="1.0.0",
)


@app.get("/", summary="Root endpoint")
async def root():
    return {
        "status": "online",
        "service": os.getenv("APP_NAME", "fastapi-postgres"),
        "version": "1.0.0",
    }


@app.get("/health", summary="Health & DB connectivity check")
async def health():
    db_ok, db_msg = await check_db_connection()
    status_code = 200 if db_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if db_ok else "unhealthy",
            "database": {"connected": db_ok, "detail": db_msg},
        },
    )
