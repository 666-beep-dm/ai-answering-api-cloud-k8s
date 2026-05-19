"""prod_app/schemas.py — Pydantic-схемы для валидации входных и выходных данных."""

from pydantic import BaseModel, EmailStr, field_validator


# ─── Users ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str
    email: EmailStr

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be empty")
        return v.strip()


class UserResponse(BaseModel):
    id: int
    name: str
    email: str


# ─── Tasks ────────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    user_id: int

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title must not be empty")
        return v.strip()


class TaskResponse(BaseModel):
    id: int
    title: str
    done: bool
    user_id: int
