"""
AI Answering API — entry point.
Single endpoint: POST /ask
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from openai import AsyncOpenAI, APIError

from config.settings import settings
from app.schemas import QuestionRequest, AnswerResponse

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.getLevelName(settings.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ai_api")

# ── OpenAI client ─────────────────────────────────────────────────────────────
_client = AsyncOpenAI(api_key=settings.openai_api_key)


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting up AI Answering API...")
    yield
    logger.info("Shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Answering API",
    description="Junior-level FastAPI service — answers questions via GPT-4o-mini.",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Request logging middleware ────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({elapsed_ms}ms)")
    return response


# ── Global exception handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


# ── Helper: call LLM ──────────────────────────────────────────────────────────
async def _ask_llm(question: str) -> str:
    """Send question to GPT-4o-mini or return mock answer."""
    if settings.use_mock:
        logger.info("Mock mode active — returning stub answer.")
        return f"[MOCK] You asked: {question}"

    try:
        response = await _client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": question}],
        )
        return response.choices[0].message.content or ""
    except APIError as exc:
        logger.error(f"OpenAI API error: {exc}")
        raise


# ── Endpoint ──────────────────────────────────────────────────────────────────
@app.post("/ask", response_model=AnswerResponse)
async def ask(body: QuestionRequest) -> AnswerResponse:
    """
    Submit a question and receive an AI-generated answer.

    - Returns **400** if the question is empty.
    - Returns **500** if the LLM call fails.
    """
    logger.info(f"Received question: {body.question[:80]}")

    try:
        answer = await _ask_llm(body.question)
    except APIError as exc:
        return JSONResponse(
            status_code=500,
            content={"detail": f"LLM service error: {str(exc)}"},
        )

    return AnswerResponse(answer=answer)
