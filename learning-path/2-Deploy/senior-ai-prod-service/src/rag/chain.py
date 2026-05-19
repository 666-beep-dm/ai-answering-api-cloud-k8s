"""
RAG chain: Retrieval → Prompt → LLM (streaming).
Uses LCEL (LangChain Expression Language) for composability.
"""
import logging
import time
from typing import AsyncIterator

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import Document
from langchain.schema.output_parser import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from src.config import get_settings
from src.metrics import llm_latency_seconds

logger = logging.getLogger(__name__)

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a helpful AI assistant. "
                "Answer the question ONLY using the provided context. "
                "If the context does not contain the answer, say so clearly. "
                "Be concise and cite sources when possible.\n\n"
                "Context:\n{context}"
            ),
        ),
        ("human", "{question}"),
    ]
)


def _format_docs(docs: list[Document]) -> str:
    parts = []
    for i, doc in enumerate(docs, 1):
        src = doc.metadata.get("source", "unknown")
        parts.append(f"[{i}] (source: {src})\n{doc.page_content}")
    return "\n\n".join(parts)


def build_chain():
    s = get_settings()
    llm = ChatOpenAI(
        model=s.openai_model,
        openai_api_key=s.openai_api_key,
        streaming=True,
        temperature=0.1,
        max_tokens=1024,
    )
    chain = (
        {"context": RunnablePassthrough(), "question": RunnablePassthrough()}
        | RAG_PROMPT
        | llm
        | StrOutputParser()
    )
    return chain


async def generate_answer(
    question: str, docs: list[Document]
) -> str:
    """Non-streaming full answer — used for cache writes."""
    chain = build_chain()
    context = _format_docs(docs)
    t0 = time.perf_counter()

    answer_parts = []
    async for chunk in chain.astream(
        {"context": context, "question": question}
    ):
        answer_parts.append(chunk)

    elapsed = time.perf_counter() - t0
    llm_latency_seconds.observe(elapsed)
    return "".join(answer_parts)


async def stream_answer(
    question: str, docs: list[Document]
) -> AsyncIterator[str]:
    """Streaming generator — yields SSE-ready text tokens."""
    chain = build_chain()
    context = _format_docs(docs)
    t0 = time.perf_counter()

    async for chunk in chain.astream(
        {"context": context, "question": question}
    ):
        yield chunk

    elapsed = time.perf_counter() - t0
    llm_latency_seconds.observe(elapsed)
    logger.info(
        "stream_complete",
        extra={"question_prefix": question[:60], "latency_ms": round(elapsed * 1000, 2)},
    )
