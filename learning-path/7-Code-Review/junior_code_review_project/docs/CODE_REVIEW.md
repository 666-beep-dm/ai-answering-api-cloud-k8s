# Code Review Report: Legacy → Refactored

> **Аудитор:** Senior Python Developer  
> **Проект:** FastAPI CRUD (users + tasks)  
> **Дата:** 2024  

---

## Что проверялось

`legacy_app/main.py` — единый файл с роутерами, бизнес-логикой и подключением к БД.

---

## Таблица найденных проблем

| # | Категория | Где в legacy | Проблема | Почему это плохо | Как исправлено в prod_app |
|---|-----------|--------------|----------|------------------|---------------------------|
| 1 | **Именование (PEP8)** | `getUsers`, `createUser`, `getTasks`… | camelCase вместо snake_case | Нарушает PEP8, усложняет читаемость и инструменты линтинга | Переименовано: `get_users`, `create_user`, `get_tasks` и т.д. |
| 2 | **Именование (смысл)** | `data1`, `tmp`, `d` | Непонятные, бессмысленные имена переменных | Через 2 недели сам автор не поймёт код; командная работа невозможна | Заменено на `payload`, `row`, `rows` |
| 3 | **Структура** | Весь код в `main.py` | Роутеры, инициализация БД и бизнес-логика в одном файле | Нарушает SRP; файл растёт бесконтрольно; невозможно тестировать по частям | Разделено на `routers/users.py`, `routers/tasks.py`, `database.py`, `schemas.py` |
| 4 | **Дублирование кода** | `conn = sqlite3.connect("legacy.db")` — 8 раз | Подключение к БД копипастой в каждом эндпоинте | Если путь к БД изменится — надо менять в 8 местах; высокий риск ошибки | Единый `get_db()` async context manager в `database.py` |
| 5 | **Дублирование кода** | Блоки `if "name" not in data1…` повторяются | Ручная валидация скопирована в `create_user` и `create_task` | DRY-нарушение; логика расходится при независимом изменении | Валидация вынесена в Pydantic-схемы (`UserCreate`, `TaskCreate`) с `field_validator` |
| 6 | **Обработка ошибок** | `get_user`, `get_task` | Возвращается `None` без HTTPException при отсутствии записи | Клиент получает `null` с кодом 200 вместо чёткого 404; API-контракт нарушен | `if row is None: raise HTTPException(404, "not found")` |
| 7 | **Обработка ошибок** | `except: pass` в `delete_user`, `delete_task` | Пустой перехват всех исключений | Реальные ошибки (нет таблицы, нет прав) молча глотаются; отладка невозможна | Используется `cursor.rowcount == 0` + правильный `HTTPException(404)` |
| 8 | **Читаемость / Type Hinting** | `def getUsers()`, `def deleteUser(id)` | Нет аннотаций типов | IDE не может подсказать тип; mypy/pyright не работают; онбординг сложнее | Все функции аннотированы: `async def get_users() -> list[UserResponse]` |
| 9 | **Читаемость / Pydantic** | `createUser(data1: dict)` | Входные данные — сырой `dict`; тело запроса не валидируется | FastAPI не генерирует Swagger-схему; любой невалидный payload падает с 500 | Входные данные — Pydantic-модели `UserCreate`, `TaskCreate` |
| 10 | **Структура / Async** | `def getUsers()`, `def createUser()` и все остальные | Синхронные `def` с блокирующим `sqlite3` | В async FastAPI-приложении синхронный I/O блокирует event loop; деградация производительности | Все хендлеры — `async def`; БД — `aiosqlite` |

---

## Детальный разбор

### ❌ Ошибка 1 — Нарушение PEP8 в именах функций

```python
# legacy_app
def getUsers():   # ← неверно
def createUser(): # ← неверно

# prod_app
async def get_users():   # ✅
async def create_user(): # ✅
```

**Почему важно:** PEP8 — де-факто стандарт Python-сообщества. Линтеры (flake8, ruff) выдадут ошибки; CI может упасть.

---

### ❌ Ошибка 2 — Непонятные переменные

```python
# legacy_app
d = conn.execute(...).fetchall()  # что такое d?
tmp = conn.execute(...).fetchone() # временная переменная на постоянном месте

# prod_app
rows = await cursor.fetchall()   # ✅ сразу понятно
row  = await cursor.fetchone()   # ✅
```

---

### ❌ Ошибка 3 — Всё в одном файле

```
legacy_app/
  main.py   ← 150+ строк: роутеры + БД + инициализация + бизнес-логика

prod_app/
  main.py          ← только create_app() и lifespan
  database.py      ← только get_db() и init_db()
  schemas.py       ← только Pydantic-модели
  routers/
    users.py       ← только роутер пользователей
    tasks.py       ← только роутер задач
```

---

### ❌ Ошибка 4 — Дублирование подключения к БД

```python
# legacy_app — 8 раз подряд в разных функциях:
conn = sqlite3.connect("legacy.db")
# ...
conn.close()

# prod_app — один раз, переиспользуется везде:
@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        yield db
```

---

### ❌ Ошибка 5 — Дублирование валидации

```python
# legacy_app — скопировано в create_user И create_task:
if "name" not in data1 or data1["name"] == "":
    return {"error": "name required"}

# prod_app — один раз в схеме:
class UserCreate(BaseModel):
    name: str

    @field_validator("name")
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("name must not be empty")
        return v
```

---

### ❌ Ошибка 6 — Нет 404 при отсутствии записи

```python
# legacy_app — клиент получает HTTP 200 + null
return tmp   # tmp может быть None!

# prod_app — чёткий HTTP 404
if row is None:
    raise HTTPException(status_code=404, detail="User not found")
```

---

### ❌ Ошибка 7 — Пустой except: pass

```python
# legacy_app
try:
    conn.execute("DELETE FROM users WHERE id=?", (id,))
except:   # ← ловит ВСЁ, включая KeyboardInterrupt!
    pass  # ← молча игнорирует

# prod_app — явная проверка через rowcount
async with db.execute("DELETE FROM users WHERE id = ?", (user_id,)) as cursor:
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="User not found")
```

---

### ❌ Ошибка 8 — Отсутствие Type Hints

```python
# legacy_app
def getUserById(id):  # id — int? str? что возвращает?
    ...

# prod_app
async def get_user(user_id: int) -> UserResponse:
    ...
```

---

### ❌ Ошибка 9 — Сырой dict вместо Pydantic

```python
# legacy_app
def createUser(data1: dict):  # ← нет Swagger, нет валидации, нет автодокументации
    name = data1["name"]      # ← KeyError, если поле отсутствует

# prod_app
async def create_user(payload: UserCreate) -> UserResponse:  # ← автовалидация + Swagger
    ...
```

---

### ❌ Ошибка 10 — Синхронный I/O в async-приложении

```python
# legacy_app — блокирует event loop!
def getUsers():
    conn = sqlite3.connect("legacy.db")  # синхронный, блокирующий
    ...

# prod_app — не блокирует event loop
async def get_users() -> list[UserResponse]:
    async with get_db() as db:           # aiosqlite — асинхронный
        ...
```

---

## Итог

Все 10 ошибок устранены в `prod_app/`. Рефакторинг улучшил:

- ✅ Читаемость и соответствие PEP8
- ✅ Тестируемость (модульная структура)
- ✅ Надёжность (корректная обработка ошибок)
- ✅ Производительность (async I/O)
- ✅ Самодокументируемость (Pydantic → Swagger UI)
