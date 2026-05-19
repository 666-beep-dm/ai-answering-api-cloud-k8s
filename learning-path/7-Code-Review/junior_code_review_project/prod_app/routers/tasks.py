"""prod_app/routers/tasks.py — роутер для сущности Task."""

from fastapi import APIRouter, HTTPException, status
from ..database import get_db
from ..schemas import TaskCreate, TaskResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=list[TaskResponse])
async def get_tasks() -> list[TaskResponse]:
    async with get_db() as db:
        async with db.execute("SELECT id, title, done, user_id FROM tasks") as cursor:
            rows = await cursor.fetchall()
    return [
        TaskResponse(id=r["id"], title=r["title"], done=bool(r["done"]), user_id=r["user_id"])
        for r in rows
    ]


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate) -> TaskResponse:
    async with get_db() as db:
        # Проверяем, что пользователь существует
        async with db.execute("SELECT id FROM users WHERE id = ?", (payload.user_id,)) as cur:
            if await cur.fetchone() is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User {payload.user_id} not found",
                )
        try:
            async with db.execute(
                "INSERT INTO tasks (title, user_id) VALUES (?, ?)",
                (payload.title, payload.user_id),
            ) as cursor:
                new_id = cursor.lastrowid
            await db.commit()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not create task: {exc}",
            )
    return TaskResponse(id=new_id, title=payload.title, done=False, user_id=payload.user_id)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int) -> TaskResponse:
    async with get_db() as db:
        async with db.execute(
            "SELECT id, title, done, user_id FROM tasks WHERE id = ?", (task_id,)
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return TaskResponse(id=row["id"], title=row["title"], done=bool(row["done"]), user_id=row["user_id"])


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int) -> None:
    async with get_db() as db:
        async with db.execute("DELETE FROM tasks WHERE id = ?", (task_id,)) as cursor:
            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
                )
        await db.commit()
