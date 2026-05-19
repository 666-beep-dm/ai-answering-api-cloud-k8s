"""prod_app/database.py — единая точка подключения к БД."""

import aiosqlite
from contextlib import asynccontextmanager

DB_PATH = "prod.db"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                name  TEXT    NOT NULL,
                email TEXT    NOT NULL UNIQUE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                title   TEXT    NOT NULL,
                done    INTEGER NOT NULL DEFAULT 0,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await db.commit()


@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db
