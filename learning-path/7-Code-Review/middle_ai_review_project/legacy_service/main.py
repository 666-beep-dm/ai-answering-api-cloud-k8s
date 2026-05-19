"""
legacy_service/main.py
──────────────────────────────────────────────────────────────────────────────
Имитация «реального» коммерческого AI-сервиса, написанного Junior/Middle-ом
без понимания архитектурных принципов.

АНТИПАТТЕРНЫ (помечены inline-комментариями):
  #! ARCH   — архитектура / разделение ответственности
  #! SEC    — безопасность
  #! LOG    — логирование / маскирование
  #! ENV    — управление окружением
  #! ASYNC  — блокировка event loop
  #! TYPE   — типизация / качество API
  #! PERF   — производительность
──────────────────────────────────────────────────────────────────────────────
"""

import os
import psycopg2                   #! ASYNC: синхронный драйвер блокирует event loop
from fastapi import FastAPI, Request
from openai import OpenAI         #! ASYNC: синхронный клиент блокирует event loop

app = FastAPI()

# ─── ENV ──────────────────────────────────────────────────────────────────────
OPENAI_KEY = "sk-hardcoded-key-1234567890abcdef"   #! SEC + ENV: захардкожен
DB_URL = os.environ.get("DATABASE_URL")             #! ENV: сырой os.environ, нет валидации

# ─── ARCH: роутер напрямую использует SDK и пишет SQL ────────────────────────

@app.post("/chat")
async def chat(request: Request):                   #! TYPE: нет Pydantic-схемы
    data = await request.json()                     #! TYPE: сырой dict без валидации
    user_message = data["message"]                  #! SEC: нет валидации/санитизации
    user_id = data["user_id"]

    print(f"[INFO] user_id={user_id} message={user_message}")  #! LOG: print + утечка PII

    # #! ASYNC: синхронный OpenAI-клиент в async def → блокирует event loop
    client = OpenAI(api_key=OPENAI_KEY)             #! ARCH + ASYNC: инициализация внутри хэндлера
    response = client.chat.completions.create(      #! ASYNC: blocking I/O
        model="gpt-4o",
        messages=[{"role": "user", "content": user_message}],
    )
    ai_text = response.choices[0].message.content

    print(f"[INFO] OpenAI response: {ai_text}")     #! LOG: ответ LLM в логах без маскировки

    # #! ARCH + SEC: сырой SQL в роутере + SQL-инъекция
    conn = psycopg2.connect(DB_URL)                 #! ASYNC + ARCH: синхронное подключение к БД
    cur = conn.cursor()
    cur.execute(
        f"INSERT INTO messages (user_id, message, response) "  #! SEC: f-string → SQL injection
        f"VALUES ({user_id}, '{user_message}', '{ai_text}')"
    )
    conn.commit()
    cur.close()
    conn.close()                                    #! PERF: новое соединение на каждый запрос

    return {"response": ai_text}                    #! TYPE: нет Pydantic Response-схемы


@app.get("/history")
async def history(request: Request):                #! TYPE: нет схемы для query-параметров
    user_id = request.query_params.get("user_id")  #! SEC: нет валидации типа
    print(f"[DEBUG] Fetching history for {user_id}")#! LOG: print, PII в логах

    # #! ARCH + SEC: SQL-инъекция, сырой SQL в роутере
    conn = psycopg2.connect(DB_URL)                 #! ASYNC + PERF: новое соединение
    cur = conn.cursor()
    cur.execute(
        f"SELECT message, response FROM messages WHERE user_id = {user_id}"  #! SEC: injection
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return {"history": rows}                        #! TYPE: нет схемы


@app.post("/summarize")
async def summarize(request: Request):              #! TYPE
    data = await request.json()                     #! TYPE
    text = data["text"]

    print(f"[INFO] Summarizing: {text[:200]}")      #! LOG: содержимое запроса в лог

    # #! ASYNC: снова синхронный клиент, снова блокировка
    client = OpenAI(api_key=OPENAI_KEY)
    result = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Summarize the following text."},
            {"role": "user", "content": text},
        ],
    )
    summary = result.choices[0].message.content

    # #! PERF: N+1 — для каждого запроса открывается и закрывается соединение
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    # #! SEC: SQL-инъекция
    cur.execute(f"INSERT INTO summaries (text, summary) VALUES ('{text}', '{summary}')")
    conn.commit()
    cur.close()
    conn.close()

    return {"summary": summary}                     #! TYPE


@app.get("/models")
async def list_models():
    # #! SEC + ENV: ключ видит любой, кто прочитает лог
    print(f"[DEBUG] Using API key: {OPENAI_KEY}")   #! LOG + SEC: ключ в stdout!

    # #! ASYNC + ARCH: ещё один синхронный вызов
    client = OpenAI(api_key=OPENAI_KEY)
    models = client.models.list()
    return {"models": [m.id for m in models.data]}  #! TYPE
