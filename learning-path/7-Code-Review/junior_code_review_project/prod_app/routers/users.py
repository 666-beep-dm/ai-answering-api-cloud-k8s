"""prod_app/routers/users.py — роутер для сущности User."""

from fastapi import APIRouter, HTTPException, status
from ..database import get_db
from ..schemas import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserResponse])
async def get_users() -> list[UserResponse]:
    async with get_db() as db:
        async with db.execute("SELECT id, name, email FROM users") as cursor:
            rows = await cursor.fetchall()
    return [UserResponse(id=r["id"], name=r["name"], email=r["email"]) for r in rows]


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate) -> UserResponse:
    async with get_db() as db:
        try:
            async with db.execute(
                "INSERT INTO users (name, email) VALUES (?, ?)",
                (payload.name, payload.email),
            ) as cursor:
                new_id = cursor.lastrowid
            await db.commit()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not create user: {exc}",
            )
    return UserResponse(id=new_id, name=payload.name, email=payload.email)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int) -> UserResponse:
    async with get_db() as db:
        async with db.execute(
            "SELECT id, name, email FROM users WHERE id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(id=row["id"], name=row["name"], email=row["email"])


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int) -> None:
    async with get_db() as db:
        async with db.execute("DELETE FROM users WHERE id = ?", (user_id,)) as cursor:
            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )
        await db.commit()
