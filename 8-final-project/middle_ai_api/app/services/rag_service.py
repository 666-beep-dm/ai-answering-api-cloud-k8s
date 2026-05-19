"""
RAG pipeline:
  1. Extract text from .txt / .pdf files.
  2. Recursive character splitting with overlap.
  3. Embed with sentence-transformers/all-MiniLM-L6-v2.
  4. Store / search with FAISS (persisted to ./vector_db).
"""

import asyncio
import os
import pickle
from typing import Optional

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Globals (initialised once on startup) ────────────────────────────────────
_embedder: Optional[SentenceTransformer] = None
_index: Optional[faiss.IndexFlatIP] = None   # Inner-Product == cosine on L2-normed vecs
_chunks: list[str] = []                       # parallel list to FAISS index rows

_INDEX_PATH = os.path.join(settings.vector_db_path, "faiss.index")
_CHUNKS_PATH = os.path.join(settings.vector_db_path, "chunks.pkl")
_DIM = 384   # all-MiniLM-L6-v2 output dimension


# ── Initialisation ────────────────────────────────────────────────────────────

def _load_or_create_index() -> faiss.IndexFlatIP:
    if os.path.exists(_INDEX_PATH):
        logger.info("Loading existing FAISS index from disk.")
        return faiss.read_index(_INDEX_PATH)
    logger.info("Creating new FAISS index.")
    return faiss.IndexFlatIP(_DIM)


def init_rag() -> None:
    """Called once at application startup (in the main lifespan)."""
    global _embedder, _index, _chunks

    os.makedirs(settings.vector_db_path, exist_ok=True)

    logger.info(f"Loading embedding model: {settings.embedding_model}")
    _embedder = SentenceTransformer(settings.embedding_model)

    _index = _load_or_create_index()

    if os.path.exists(_CHUNKS_PATH):
        with open(_CHUNKS_PATH, "rb") as f:
            _chunks = pickle.load(f)
        logger.info(f"Loaded {len(_chunks)} existing chunks.")


def _save_index() -> None:
    faiss.write_index(_index, _INDEX_PATH)
    with open(_CHUNKS_PATH, "wb") as f:
        pickle.dump(_chunks, f)


# ── Text extraction ───────────────────────────────────────────────────────────

def _extract_text(data: bytes, filename: str) -> str:
    ext = os.path.splitext(filename)[-1].lower()
    if ext == ".txt":
        return data.decode("utf-8", errors="replace")
    if ext == ".pdf":
        try:
            import io
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(data))
            return "\n".join(
                page.extract_text() or "" for page in reader.pages
            )
        except Exception as exc:
            logger.warning(f"PDF parse error: {exc}")
            return data.decode("utf-8", errors="replace")
    return data.decode("utf-8", errors="replace")


# ── Chunking ──────────────────────────────────────────────────────────────────

def _recursive_split(text: str, size: int, overlap: int) -> list[str]:
    """Simple recursive character splitter."""
    separators = ["\n\n", "\n", ". ", " ", ""]
    for sep in separators:
        parts = text.split(sep) if sep else list(text)
        chunks, current = [], ""
        for part in parts:
            candidate = current + (sep if current else "") + part
            if len(candidate) <= size:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = part
        if current:
            chunks.append(current)

        # If every chunk is within size limit we are done
        if all(len(c) <= size for c in chunks):
            # Apply overlap
            result = []
            for i, chunk in enumerate(chunks):
                if i == 0:
                    result.append(chunk)
                else:
                    tail = chunks[i - 1][-overlap:]
                    result.append(tail + chunk if tail else chunk)
            return result
    return [text]


# ── Public async API ──────────────────────────────────────────────────────────

async def index_document(data: bytes, filename: str) -> int:
    """Ingest a document: extract → chunk → embed → store. Returns chunk count."""
    if _embedder is None or _index is None:
        raise RuntimeError("RAG not initialised — call init_rag() first.")

    text = await asyncio.to_thread(_extract_text, data, filename)
    if not text.strip():
        logger.warning(f"No text extracted from {filename}")
        return 0

    new_chunks = _recursive_split(text, settings.chunk_size, settings.chunk_overlap)
    logger.info(f"{filename}: {len(new_chunks)} chunks created.")

    # Embed in a thread to avoid blocking the event loop
    vectors: np.ndarray = await asyncio.to_thread(
        _embedder.encode, new_chunks, normalize_embeddings=True
    )
    vectors = np.array(vectors, dtype="float32")

    _index.add(vectors)
    _chunks.extend(new_chunks)

    await asyncio.to_thread(_save_index)
    return len(new_chunks)


async def retrieve(question: str) -> list[str]:
    """Return the top-k most relevant chunks for the question."""
    if _embedder is None or _index is None or _index.ntotal == 0:
        return []

    q_vec: np.ndarray = await asyncio.to_thread(
        _embedder.encode, [question], normalize_embeddings=True
    )
    q_vec = np.array(q_vec, dtype="float32")

    k = min(settings.top_k_chunks, _index.ntotal)
    _, indices = _index.search(q_vec, k)

    return [_chunks[i] for i in indices[0] if i != -1]


def index_ready() -> bool:
    return _index is not None and _index.ntotal > 0
