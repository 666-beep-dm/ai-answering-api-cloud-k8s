"""Qdrant async vector store integration."""
import asyncio, uuid
from typing import Optional

import numpy as np
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)
_s = get_settings()

_client: Optional[AsyncQdrantClient] = None
_DIM = 384  # all-MiniLM-L6-v2


async def init_qdrant() -> None:
    global _client
    _client = AsyncQdrantClient(host=_s.qdrant_host, port=_s.qdrant_port)
    collections = [c.name for c in (await _client.get_collections()).collections]
    if _s.qdrant_collection not in collections:
        await _client.create_collection(
            _s.qdrant_collection,
            vectors_config=VectorParams(size=_DIM, distance=Distance.COSINE),
        )
    logger.info(f"Qdrant ready — collection: {_s.qdrant_collection}")


async def close_qdrant() -> None:
    if _client:
        await _client.close()


async def upsert(vectors: np.ndarray, texts: list[str]) -> None:
    if _client is None:
        raise RuntimeError("Qdrant not initialised.")
    points = [
        PointStruct(id=str(uuid.uuid4()), vector=v.tolist(), payload={"text": t})
        for v, t in zip(vectors, texts)
    ]
    await _client.upsert(_s.qdrant_collection, points=points)


async def search(query_vector: np.ndarray, k: int = 3) -> list[str]:
    if _client is None or not await health_check():
        return []
    results = await _client.search(
        _s.qdrant_collection, query_vector=query_vector.tolist(), limit=k
    )
    return [r.payload["text"] for r in results]  # type: ignore


async def health_check() -> bool:
    try:
        await _client.get_collections()  # type: ignore
        return True
    except Exception:
        return False
