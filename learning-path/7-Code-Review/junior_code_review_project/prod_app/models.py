"""prod_app/models.py — лёгкие dataclass-модели для маппинга строк БД."""

from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str
    email: str


@dataclass
class Task:
    id: int
    title: str
    done: bool
    user_id: int
