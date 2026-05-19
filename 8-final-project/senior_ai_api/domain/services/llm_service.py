"""LLM streaming service — returns an async generator of token strings."""
import asyncio
from collections.abc import AsyncIterator

from openai import AsyncOpenAI, APIError

from core.config import get_settings
from core.logging import get_logger
from core.metrics import llm_tokens_total

logger = get_logger(__name__)
_s = get_settings()
_client = AsyncOpenAI(api_key=_s.openai_api_key)

_SYSTEM = (
    "You are a precise assistant. Answer ONLY using the provided context. "
    "If the answer is not in the context, state that clearly."
)


def _build_prompt(question: str, chunks: list[str]) -> str:
    ctx = "\n\n---\n\n".join(chunks) if chunks else "(No context available)"
    return f"CONTEXT:\n{ctx}\n\nQUESTION: {question}"


async def stream_answer(question: str, chunks: list[str]) -> AsyncIterator[str]:
    """Yield answer tokens as they arrive from the LLM."""
    if _s.use_mock:
        for word in f"[MOCK] Answer to: {question}".split():
            yield word + " "
            await asyncio.sleep(0.02)
        return

    prompt = _build_prompt(question, chunks)
    llm_tokens_total.labels(type="prompt").inc(len(prompt.split()))

    retries, base = 3, 1.0
    for attempt in range(1, retries + 1):
        try:
            stream = await _client.chat.completions.create(
                model=_s.openai_model,
                messages=[
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                stream=True,
            )
            async for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                if token:
                    llm_tokens_total.labels(type="completion").inc(1)
                    yield token
            return
        except APIError as e:
            delay = base * 2 ** (attempt - 1)
            logger.warning(f"LLM error (attempt {attempt}): {e} — retry in {delay}s")
            await asyncio.sleep(delay)
    yield "[ERROR] LLM unavailable after retries."
