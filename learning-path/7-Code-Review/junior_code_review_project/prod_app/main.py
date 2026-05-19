"""prod_app/main.py — точка входа в приложение."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .database import init_db
from .routers import users, tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Task Manager API",
        description="Пример профессионально написанного FastAPI CRUD-приложения",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.include_router(users.router)
    app.include_router(tasks.router)
    return app


app = create_app()
