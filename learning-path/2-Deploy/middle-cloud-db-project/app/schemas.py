from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class ItemBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, examples=["Buy groceries"])
    description: str | None = Field(None, examples=["Milk, eggs, bread"])
    is_active: bool = Field(True)


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    is_active: bool | None = None


class ItemResponse(ItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class PaginatedItems(BaseModel):
    total: int
    items: list[ItemResponse]
