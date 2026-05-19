import os
from fastapi import FastAPI

app = FastAPI(title="middle-k8s-app")

APP_COLOR         = os.getenv("APP_COLOR", "blue")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "")
APP_ENV           = os.getenv("APP_ENV", "development")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "env":   APP_ENV,
        "color": APP_COLOR,
        # never expose secrets in real apps — shown here for demo only
        "db_password_set": bool(DATABASE_PASSWORD),
    }


@app.get("/info")
def info():
    return {
        "app_color": APP_COLOR,
        "environment": APP_ENV,
    }
