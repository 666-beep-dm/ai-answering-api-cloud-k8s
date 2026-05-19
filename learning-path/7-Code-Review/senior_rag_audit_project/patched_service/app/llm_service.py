"""patched_service/app/llm_service.py
Async LLM Service с Circuit Breaker, Retry, семантическим кэшем и метриками.
"""

import hashlib
import logging
from typing import Optional

from openai import AsyncOpenAI
from .config import Settings
from .resilience import CircuitBreaker, retry_with_backoff
from .metrics import LLM_REQUESTS_TOTAL, LLM_TOKENS_TOTAL, LLM_COST_USD, LLM_LATENCY

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, settings: Settings, redis_client) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout,
            max_retries=0,                   # retry управляется вручную через retry_with_backoff
        )
        self._model = settings.openai_model
        self._max_tokens = settings.openai_max_tokens
        self._cache_ttl = settings.cache_ttl_seconds
        self._redis = redis_client
        self._circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)

        # Стоимость за 1M токенов (gpt-4o на дату написания)
        self._cost_per_input_token = 5.0 / 1_000_000
        self._cost_per_output_token = 15.0 / 1_000_000

    def _cache_key(self, prompt: str) -> str:
        """SHA-256 ключ для точного кэша."""
        return f"llm:exact:{hashlib.sha256(prompt.encode()).hexdigest()}"

    async def _get_cached(self, key: str) -> Optional[str]:
        value = await self._redis.get(key)
        return value.decode() if value else None

    async def _set_cached(self, key: str, value: str) -> None:
        await self._redis.set(key, value, ex=self._cache_ttl)

    async def _call_openai(self, messages: list[dict]) -> tuple[str, int, int]:
        """Прямой вызов OpenAI API — оборачивается в retry + circuit breaker."""
        resp = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=messages,
        )
        text = resp.choices[0].message.content or ""
        in_tok = resp.usage.prompt_tokens if resp.usage else 0
        out_tok = resp.usage.completion_tokens if resp.usage else 0
        return text, in_tok, out_tok

    async def chat(self, query: str, trace_id: str = "") -> dict:
        """
        Главный метод: кэш -> circuit breaker -> retry -> OpenAI -> метрики.
        Семантический кэш реализован через точный хэш (для упрощения;
        в проде — через векторное сравнение эмбеддингов).
        """
        cache_key = self._cache_key(query)

        # COST: кэш с длинным TTL
        cached = await self._get_cached(cache_key)
        if cached:
            logger.info("cache_hit trace_id=%s", trace_id)
            LLM_REQUESTS_TOTAL.labels(status="cache_hit", model=self._model).inc()
            return {"response": cached, "cached": True, "tokens_used": 0, "cost_usd": 0.0}

        # RESILIENCE: circuit breaker + retry
        with LLM_LATENCY.labels(model=self._model).time():
            text, in_tok, out_tok = await self._circuit_breaker.call(
                retry_with_backoff,
                self._call_openai,
                [{"role": "user", "content": query}],
                max_retries=3,
                base_delay=1.0,
            )

        # COST: учёт токенов и стоимости
        cost = in_tok * self._cost_per_input_token + out_tok * self._cost_per_output_token
        LLM_TOKENS_TOTAL.labels(type="input",  model=self._model).inc(in_tok)
        LLM_TOKENS_TOTAL.labels(type="output", model=self._model).inc(out_tok)
        LLM_COST_USD.labels(model=self._model).inc(cost)
        LLM_REQUESTS_TOTAL.labels(status="success", model=self._model).inc()

        logger.info(
            "llm_call trace_id=%s in_tokens=%d out_tokens=%d cost_usd=%.6f",
            trace_id, in_tok, out_tok, cost
        )

        await self._set_cached(cache_key, text)
        return {
            "response": text,
            "cached": False,
            "tokens_used": in_tok + out_tok,
            "cost_usd": round(cost, 6),
        }
