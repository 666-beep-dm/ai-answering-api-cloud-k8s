"""
Vector retriever built on LangChain + FAISS in-memory store.
In production: swap FAISS for pgvector (langchain-postgres) or Chroma.
"""
import logging
import time
from pathlib import Path

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document

from src.config import get_settings
from src.metrics import retrieval_latency_seconds

logger = logging.getLogger(__name__)

_vectorstore: FAISS | None = None


def _build_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=get_settings().embedding_model,
        openai_api_key=get_settings().openai_api_key,
    )


async def load_vectorstore() -> None:
    """
    Initialise vector store.
    Loads from disk if index exists, otherwise creates a stub index
    with a welcome document so the service starts without error.
    """
    global _vectorstore
    index_path = Path("data/faiss_index")

    if index_path.exists():
        logger.info("Loading FAISS index from %s", index_path)
        _vectorstore = FAISS.load_local(
            str(index_path),
            _build_embeddings(),
            allow_dangerous_deserialization=True,
        )
    else:
        logger.warning(
            "No FAISS index found — creating stub. "
            "Ingest real documents via /ingest or scripts/ingest.py"
        )
        stub_docs = [
            Document(
                page_content="This is a placeholder document. Please ingest real data.",
                metadata={"source": "stub"},
            )
        ]
        _vectorstore = FAISS.from_documents(stub_docs, _build_embeddings())

    logger.info("Vector store ready — %d vectors", _vectorstore.index.ntotal)


async def retrieve(question: str, top_k: int = 4) -> list[Document]:
    if _vectorstore is None:
        raise RuntimeError("Vector store not initialised")

    t0 = time.perf_counter()
    docs_and_scores = _vectorstore.similarity_search_with_score(
        question, k=top_k
    )
    elapsed = time.perf_counter() - t0
    retrieval_latency_seconds.observe(elapsed)

    logger.info(
        "retrieval_complete",
        extra={
            "question_prefix": question[:60],
            "num_docs": len(docs_and_scores),
            "latency_ms": round(elapsed * 1000, 2),
        },
    )
    # Return only Document objects (scores attached as metadata)
    results = []
    for doc, score in docs_and_scores:
        doc.metadata["retrieval_score"] = round(float(score), 4)
        results.append(doc)
    return results
