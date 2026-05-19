"""
RAG domain service — pure business logic.
Depends on abstractions (storage), not concrete infra.
"""
import asyncio, os
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from core.config import get_settings
from core.logging import get_logger
from infrastructure.vector import qdrant_store

logger = get_logger(__name__)
_s = get_settings()

_embedder: Optional[SentenceTransformer] = None


def load_embedder() -> None:
    global _embedder
    logger.info(f"Loading embedding model: {_s.embedding_model}")
    _embedder = SentenceTransformer(_s.embedding_model)


def _extract_text(data: bytes, filename: str) -> str:
    ext = os.path.splitext(filename)[-1].lower()
    if ext == ".txt":
        return data.decode("utf-8", errors="replace")
    if ext == ".pdf":
        try:
            import io, pypdf
            return "\n".join(
                p.extract_text() or "" for p in pypdf.PdfReader(io.BytesIO(data)).pages
            )
        except Exception as e:
            logger.warning(f"PDF parse error: {e}")
    return data.decode("utf-8", errors="replace")


def _split(text: str) -> list[str]:
    """Recursive character splitter with overlap."""
    size, overlap = _s.chunk_size, _s.chunk_overlap
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        start += size - overlap
    return [c for c in chunks if c.strip()]


async def ingest(data: bytes, filename: str) -> int:
    """Extract → chunk → embed → upsert. Returns chunk count."""
    if _embedder is None:
        raise RuntimeError("Embedder not loaded.")
    text = await asyncio.to_thread(_extract_text, data, filename)
    chunks = _split(text)
    if not chunks:
        return 0
    vectors: np.ndarray = await asyncio.to_thread(
        _embedder.encode, chunks, normalize_embeddings=True, show_progress_bar=False
    )
    await qdrant_store.upsert(np.array(vectors, dtype="float32"), chunks)
    logger.info(f"Indexed {len(chunks)} chunks from {filename}")
    return len(chunks)


async def retrieve(question: str) -> list[str]:
    if _embedder is None:
        return []
    q_vec: np.ndarray = await asyncio.to_thread(
        _embedder.encode, [question], normalize_embeddings=True
    )
    return await qdrant_store.search(np.array(q_vec[0], dtype="float32"), k=_s.top_k_chunks)
