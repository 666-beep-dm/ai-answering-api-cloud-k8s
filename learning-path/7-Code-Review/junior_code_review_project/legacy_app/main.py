"""
legacy_app/main.py
Намеренно "грязный" код для учебного Code Review.
Содержит 10 классических Junior-ошибок.
"""

from fastapi import FastAPI
import sqlite3

app = FastAPI()

# ─── ОШИБКА 1 (Именование): camelCase вместо snake_case ───────────────────
# PEP8 требует get_users, create_user и т.д.
# ─── ОШИБКА 2 (Именование): непонятные переменные data1, tmp, d ───────────
# ─── ОШИБКА 3 (Структура): роутеры, БД и бизнес-логика в одном файле ──────
# ─── ОШИБКА 4 (Дублирование): подключение к БД копипастом в каждом роутере ─
# ─── ОШИБКА 5 (Дублирование): одинаковая валидация в нескольких местах ─────
# ─── ОШИБКА 6 (Ошибки): нет try/except, сырые исключения улетают в ответ ───
# ─── ОШИБКА 7 (Ошибки): пустой except: pass скрывает реальные проблемы ─────
# ─── ОШИБКА 8 (Читаемость): нет Type Hinting ни у функций, ни у переменных ─
# ─── ОШИБКА 9 (Читаемость): нет Pydantic-схем — читаем сырые dict/JSON ─────
# ─── ОШИБКА 10 (Структура): синхронные def вместо async def ─────────────────


def initDB():                          # ОШИБКА 1: camelCase
    conn = sqlite3.connect("legacy.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            done INTEGER DEFAULT 0,
            userId INTEGER
        )
    """)
    conn.commit()
    conn.close()

initDB()


# ═══════════════════════════════ USERS ════════════════════════════════════════

@app.get("/users")
def getUsers():                        # ОШИБКА 1: camelCase
    conn = sqlite3.connect("legacy.db")  # ОШИБКА 4: дублирование подключения
    d = conn.execute("SELECT * FROM users").fetchall()  # ОШИБКА 2: переменная d
    conn.close()
    return d


@app.post("/users")
def createUser(data1: dict):           # ОШИБКА 2 + 8 + 9: data1, нет типа, нет схемы
    # ОШИБКА 5: ручная валидация скопирована из другого эндпоинта
    if "name" not in data1 or data1["name"] == "":
        return {"error": "name required"}
    if "email" not in data1 or data1["email"] == "":
        return {"error": "email required"}

    conn = sqlite3.connect("legacy.db")  # ОШИБКА 4: дублирование
    conn.execute(
        "INSERT INTO users (name, email) VALUES (?, ?)",
        (data1["name"], data1["email"])
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.get("/users/{id}")
def getUserById(id):                   # ОШИБКА 8: нет типа у параметра
    conn = sqlite3.connect("legacy.db")  # ОШИБКА 4: дублирование
    tmp = conn.execute(                  # ОШИБКА 2: tmp
        "SELECT * FROM users WHERE id=?", (id,)
    ).fetchone()
    conn.close()
    # ОШИБКА 6: если tmp=None — просто вернём None без HTTPException 404
    return tmp


@app.delete("/users/{id}")
def deleteUser(id):                    # ОШИБКА 8: нет типа
    conn = sqlite3.connect("legacy.db")  # ОШИБКА 4: дублирование
    try:
        conn.execute("DELETE FROM users WHERE id=?", (id,))
        conn.commit()
    except:                            # ОШИБКА 7: пустой except: pass
        pass
    conn.close()
    return {"deleted": id}


# ═══════════════════════════════ TASKS ════════════════════════════════════════

@app.get("/tasks")
def getTasks():                        # ОШИБКА 1: camelCase
    conn = sqlite3.connect("legacy.db")  # ОШИБКА 4: дублирование
    data1 = conn.execute("SELECT * FROM tasks").fetchall()  # ОШИБКА 2
    conn.close()
    return data1


@app.post("/tasks")
def createTask(data1: dict):           # ОШИБКА 2 + 8 + 9
    # ОШИБКА 5: та же ручная валидация скопирована ещё раз
    if "title" not in data1 or data1["title"] == "":
        return {"error": "title required"}
    if "userId" not in data1:
        return {"error": "userId required"}

    conn = sqlite3.connect("legacy.db")  # ОШИБКА 4: дублирование
    conn.execute(
        "INSERT INTO tasks (title, userId) VALUES (?, ?)",
        (data1["title"], data1["userId"])
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.get("/tasks/{id}")
def getTaskById(id):                   # ОШИБКА 1 + 8
    conn = sqlite3.connect("legacy.db")  # ОШИБКА 4: дублирование
    tmp = conn.execute(                  # ОШИБКА 2
        "SELECT * FROM tasks WHERE id=?", (id,)
    ).fetchone()
    conn.close()
    # ОШИБКА 6: нет обработки None — клиент получит null без объяснений
    return tmp


@app.delete("/tasks/{id}")
def deleteTask(id):                    # ОШИБКА 8
    conn = sqlite3.connect("legacy.db")  # ОШИБКА 4: дублирование
    try:
        conn.execute("DELETE FROM tasks WHERE id=?", (id,))
        conn.commit()
    except:                            # ОШИБКА 7: пустой except
        pass
    conn.close()
    return {"deleted": id}
