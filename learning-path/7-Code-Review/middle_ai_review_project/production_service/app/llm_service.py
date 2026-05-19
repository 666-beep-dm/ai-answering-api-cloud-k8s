"""production_service/app/llm_service.py
LLM Service layer — единственный слой, который знает об OpenAI.
Использует AsyncOpenAI, не блокирует event loop.
"""

import logging
from openai import AsyncOpenAI
from .config import get_settings, Settings

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model
        self._max_tokens = settings.openai_max_tokens

    async def chat(self, message: str) -> tuple[str, int]:
        """Отправляет сообщение и возвращает (ответ, кол-во токенов)."""
        logger.info("LLM chat request, model=%s", self._model)  # ключ не логируется
        resp = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": message}],
        )
        text = resp.choices[0].message.content or ""
        tokens = resp.usage.total_tokens if resp.usage else 0
        logger.debug("LLM chat completed, tokens=%d", tokens)
        return text, tokens

    async def summarize(self, text: str) -> tuple[str, int]:
        """Суммаризирует текст."""
        logger.info("LLM summarize request, chars=%d", len(text))
        resp = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[
                {"role": "system", "content": "Summarize the following text concisely."},
                {"role": "user", "content": text},
            ],
        )
        text_out = resp.choices[0].message.content or ""
        tokens = resp.usage.total_tokens if resp.usage else 0
        logger.debug("LLM summarize completed, tokens=%d", tokens)
        return text_out, tokens

    async def list_models(self) -> list[str]:
        """Возвращает список доступных моделей."""
        models = await self._client.models.list()
        return [m.id for m in models.data]
