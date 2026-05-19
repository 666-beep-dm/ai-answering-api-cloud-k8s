"""
Test endpoints covering the three observable scenarios:
  GET /success       → 200 OK
  GET /client-error  → 400 Bad Request
  GET /server-error  → 500 (unhandled ValueError / ZeroDivisionError)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

router = APIRouter(tags=["Test Endpoints"])


# ── /success ──────────────────────────────────────────────────────────────
@router.get("/success", summary="Returns 200 OK")
async def success():
    return {"status": "ok", "message": "Everything is fine."}


# ── /client-error ─────────────────────────────────────────────────────────
@router.get("/client-error", summary="Returns 400 Bad Request")
async def client_error():
    raise HTTPException(
        status_code=400,
        detail="Bad Request: missing required parameter 'item_id'.",
    )


# ── /server-error ─────────────────────────────────────────────────────────
@router.get("/server-error", summary="Triggers unhandled 500 with stack trace")
async def server_error():
    # Intentional ZeroDivisionError — caught by global handler → stack_trace logged
    result = 1 / 0          # noqa: F841
    return {"result": result}


# ── /validate ─────────────────────────────────────────────────────────────
class Item(BaseModel):
    name: str
    price: float

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("price must be > 0")
        return v


@router.post("/validate", summary="Triggers 422 Pydantic validation error")
async def validate_item(item: Item):
    return {"received": item.model_dump()}
