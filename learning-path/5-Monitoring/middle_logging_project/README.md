# FastAPI Advanced JSON Logging

> **Middle-level** FastAPI project — structured NDJSON logs, per-request UUID tracing,
> centralised exception handling with full stack traces, and Docker volume-mounted log files.

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM       | 8 GB    | **16 GB**   |
| CPU       | 2 cores | **4 cores** |
| OS        | Linux / macOS / Windows (WSL2) | — |
| Docker    | 24+     | latest      |
| Python    | 3.10    | 3.10+       |

---

## Architecture

```
middle_logging_project/
├── app/
│   ├── api/
│   │   └── routes.py          # GET /success  /client-error  /server-error  POST /validate
│   ├── core/
│   │   ├── logger_config.py   # JsonFormatter + setup_logging()
│   │   └── exception_handlers.py  # 4xx → WARNING | 5xx → ERROR + stack_trace
│   ├── middlewares/
│   │   └── request_context.py # UUID request_id, timing, ContextVar
│   └── main.py
├── tests/
│   └── test_endpoints.py
├── logs/                      # Mounted as Docker volume → persists on host
├── .env / .env.example
├── Dockerfile                 # Multi-stage, python:3.10-slim
├── docker-compose.yml
└── README.md
```

---

## Log Format (NDJSON)

Every record is a **single JSON line** — safe for `jq`, Loki, Elasticsearch, etc.

### Normal request
```json
{"timestamp": "2024-05-01T12:00:01.123+00:00", "level": "INFO", "logger": "app.middleware", "message": "← GET /success 200", "request_id": "a1b2-...", "path": "/success", "method": "GET", "status_code": 200, "execution_time_ms": 1.23}
```

### 4xx warning
```json
{"timestamp": "...", "level": "WARNING", "logger": "app.errors", "message": "HTTP 400: Bad Request: ...", "request_id": "c3d4-...", "path": "/client-error", "method": "GET", "status_code": 400}
```

### 5xx error with stack trace
```json
{"timestamp": "...", "level": "ERROR", "logger": "app.errors", "message": "Unhandled exception: ZeroDivisionError: division by zero", "request_id": "e5f6-...", "path": "/server-error", "method": "GET", "status_code": 500, "stack_trace": "Traceback (most recent call last):\n  ...\nZeroDivisionError: division by zero"}
```

---

## API Endpoints

| Method | Path            | Expected Status | Purpose                        |
|--------|-----------------|-----------------|--------------------------------|
| GET    | `/success`      | 200             | Happy path                     |
| GET    | `/client-error` | 400             | 4xx WARNING log                |
| GET    | `/server-error` | 500             | 5xx ERROR log + stack_trace    |
| POST   | `/validate`     | 422             | Pydantic validation → WARNING  |
| GET    | `/docs`         | 200             | Swagger UI                     |

---

## Quick Start — Docker (recommended)

```bash
# 1. Clone / unzip the project
cd middle_logging_project

# 2. Copy env template
cp .env.example .env

# 3. Build and run in background
docker-compose up --build -d

# 4. Follow structured JSON logs
docker-compose logs -f

# 5. Pretty-print with jq (install jq first)
docker-compose logs -f | grep '^{' | jq .

# 6. Open Swagger UI
#    http://localhost:8000/docs
```

To enable file logging (logs saved under `./logs/app.log` on the host):
```bash
# Edit .env:
LOG_TO_FILE=true
docker-compose up --build -d
cat logs/app.log | jq .
```

---

## Quick Start — Local (without Docker)

```bash
python -m venv .venv
source .venv/Scripts/activate   # Git Bash on Windows
# source .venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Git Bash — Initialise & Push to GitHub

```bash
git init
git add .
git commit -m "feat: advanced JSON logging and exception handling"

git remote add origin https://github.com/<your-username>/middle_logging_project.git
git branch -M main
git push -u origin main
```

---

## Docker Commands Reference

| Command                            | Description                          |
|------------------------------------|--------------------------------------|
| `docker-compose up --build`        | Build & run (foreground)             |
| `docker-compose up --build -d`     | Build & run (detached)               |
| `docker-compose logs -f`           | Follow live logs                     |
| `docker-compose logs -f \| jq .` | Pretty-printed JSON logs             |
| `docker-compose down`              | Stop and remove container            |
| `docker-compose restart`           | Restart without rebuild              |

---

## Environment Variables

| Variable     | Default      | Description                             |
|--------------|--------------|-----------------------------------------|
| `LOG_LEVEL`  | `INFO`       | `DEBUG` / `INFO` / `WARNING` / `ERROR`  |
| `LOG_TO_FILE`| `false`      | `true` → also write to `LOG_FILE`       |
| `LOG_FILE`   | `logs/app.log` | Path relative to container `/app`     |

---

## License

MIT
