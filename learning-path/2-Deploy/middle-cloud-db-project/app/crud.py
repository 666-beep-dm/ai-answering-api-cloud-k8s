from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import Item
from app.schemas import ItemCreate, ItemUpdate
import uuid


async def get_item(db: AsyncSession, item_id: str) -> Item | None:
    result = await db.execute(select(Item).where(Item.id == item_id))
    return result.scalar_one_or_none()


async def get_items(
    db: AsyncSession, skip: int = 0, limit: int = 20
) -> tuple[int, list[Item]]:
    total_result = await db.execute(select(func.count()).select_from(Item))
    total = total_result.scalar_one()

    result = await db.execute(select(Item).offset(skip).limit(limit))
    items = list(result.scalars().all())
    return total, items


async def create_item(db: AsyncSession, payload: ItemCreate) -> Item:
    item = Item(
        id=str(uuid.uuid4()),
        **payload.model_dump(),
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def update_item(
    db: AsyncSession, item: Item, payload: ItemUpdate
) -> Item:
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return item


async def delete_item(db: AsyncSession, item: Item) -> None:
    await db.delete(item)
    await db.commit()
