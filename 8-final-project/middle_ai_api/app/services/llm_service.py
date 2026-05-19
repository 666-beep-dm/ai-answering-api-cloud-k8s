"""
LLM service — wraps AsyncOpenAI with retry logic and a mock fallback.
Builds a context-grounded prompt to reduce hallucinations.
"""

import asyncio

from openai import AsyncOpenAI, APIError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_client = AsyncOpenAI(api_key=settings.openai_api_key)

_MAX_RETRIES = 3
_BASE_DELAY = 1.0


def _build_prompt(question: str, context_chunks: list[str]) -> str:
    if not context_chunks:
        context_section = "(No document context available — answer from general knowledge.)"
    else:
        context_section = "\n\n---\n\n".join(context_chunks)

    return (
        "You are a helpful assistant. Answer the question using ONLY the context "
        "provided below. If the answer cannot be found in the context, say so "
        "explicitly — do NOT invent information.\n\n"
        f"CONTEXT:\n{context_section}\n\n"
        f"QUESTION: {question}"
    )


async def ask_llm(question: str, context_chunks: list[str]) -> str:
    """Generate an answer; retries up to _MAX_RETRIES on transient API errors."""
    if settings.use_mock:
        ctx_preview = context_chunks[0][:80] if context_chunks else "none"
        return f"[MOCK] Q: {question} | top-chunk: {ctx_preview}..."

    prompt = _build_prompt(question, context_chunks)
    last_exc: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            logger.info(f"LLM call attempt {attempt}/{_MAX_RETRIES}")
            response = await _client.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content or ""
        except APIError as exc:
            last_exc = exc
            delay = _BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(f"OpenAI error (attempt {attempt}): {exc} — retry in {delay}s")
            await asyncio.sleep(delay)

    raise last_exc  # type: ignore[misc]
