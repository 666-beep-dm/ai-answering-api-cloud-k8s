# FastAPI Logging Middleware

> **Junior-level** FastAPI project demonstrating structured HTTP request logging
> via a custom `BaseHTTPMiddleware` class.

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

## Project Structure

```
junior_logging_project/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application + endpoints
│   └── middleware.py    # Custom LoggingMiddleware
├── tests/
│   ├── __init__.py
│   └── test_endpoints.py
├── .env                 # Runtime env vars (git-ignored)
├── .env.example         # Template for env vars
├── .gitignore
├── Dockerfile           # Multi-stage, python:3.10-slim
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## API Endpoints

| Method | Path     | Description                          |
|--------|----------|--------------------------------------|
| GET    | `/`      | Health check                         |
| GET    | `/slow`  | 2-second delay (tests duration log)  |
| GET    | `/error` | Simulates HTTP 500                   |
| GET    | `/docs`  | Swagger UI                           |
| GET    | `/redoc` | ReDoc                                |

---

## Quick Start (Docker — recommended)

```bash
# 1. Clone repository
git clone <your-repo-url>
cd junior_logging_project

# 2. Copy env template
cp .env.example .env

# 3. Build and run
docker-compose up --build

# 4. Open Swagger UI
# http://localhost:8000/docs
```

Expected console output example:
```
2024-05-01 12:00:01 | INFO     | → REQUEST   GET /
2024-05-01 12:00:01 | INFO     | ← RESPONSE  GET / | status=200 | 1.23 ms
2024-05-01 12:00:05 | INFO     | → REQUEST   GET /slow
2024-05-01 12:00:07 | INFO     | ← RESPONSE  GET /slow | status=200 | 2001.45 ms
2024-05-01 12:00:10 | INFO     | → REQUEST   GET /error
2024-05-01 12:00:10 | ERROR    | ← RESPONSE  GET /error | status=500 | 0.89 ms | error=...
```

---

## Quick Start (Local / without Docker)

```bash
python -m venv .venv
# Windows Git Bash:
source .venv/Scripts/activate
# Linux / macOS:
# source .venv/bin/activate

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
# Inside the project folder:
git init
git add .
git commit -m "feat: implement request logging middleware"

# Add remote and push
git remote add origin https://github.com/<your-username>/junior_logging_project.git
git branch -M main
git push -u origin main
```

---

## Docker Commands Reference

| Command                        | Description                     |
|--------------------------------|---------------------------------|
| `docker-compose up --build`    | Build image and start container |
| `docker-compose up -d`         | Start in detached mode          |
| `docker-compose logs -f`       | Follow container logs           |
| `docker-compose down`          | Stop and remove container       |
| `docker-compose restart`       | Restart running container       |

---

## Environment Variables

| Variable    | Default | Description          |
|-------------|---------|----------------------|
| `LOG_LEVEL` | `INFO`  | Python logging level |

---

## License

MIT
