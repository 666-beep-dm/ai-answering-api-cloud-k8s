# 🐳 Docker Network Debug Stand — FastAPI + PostgreSQL

**Middle-level DevOps training project**: reproduce and fix the classic
`Connection Refused / Name or service not known` error when connecting
a FastAPI container to PostgreSQL inside Docker Compose.

---

## System Requirements

| Parameter | Minimum | Recommended (dev machine) |
|-----------|---------|--------------------------|
| RAM       | 4 GB    | **16 GB**                |
| CPU       | 2 cores | **4 cores**              |
| Docker    | 24+     | latest                   |
| Docker Compose | 2.20+ | latest              |
| Python    | 3.10+   | 3.11+ (local tests only) |

---

## Project Structure

```
middle_docker_network_fix/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app + lifespan logging
│   ├── core/
│   │   ├── config.py            # Pydantic-Settings (reads .env)
│   │   ├── database.py          # SQLAlchemy 2.0 async engine + health probe
│   │   └── logging_config.py   # Structured logging setup
│   └── api/
│       └── health.py            # GET /health  &  GET /health/db
├── scripts/
│   └── wait_for_db.sh          # Fallback bash wait script
├── tests/
│   └── test_health.py          # Pytest unit tests (mocked DB)
├── .env.example                 # ✅ Correct env (DB_HOST=db)
├── .env.buggy                   # ❌ Buggy env  (DB_HOST=localhost)
├── docker-compose.yml           # ✅ Fixed Compose (healthcheck + depends_on)
├── docker-compose.buggy.yml     # ❌ Buggy Compose (no healthcheck)
├── Dockerfile                   # Multi-stage python:3.10-slim build
├── requirements.txt
└── README.md
```

---

## The Bug Explained

### What goes wrong?

```
web container                     db container
─────────────────                 ────────────────
DB_HOST=localhost  ──✗──►  127.0.0.1 (own loopback!)
                                  PostgreSQL at 172.x.x.x
```

Inside a Docker container **`localhost` resolves to the container's own
loopback interface**, not to another service. The correct hostname is the
**Compose service name** (`db`), which Docker's internal DNS resolves to the
container's IP automatically.

**Second bug**: even with the correct hostname, if `web` starts before
PostgreSQL finishes initializing, the connection attempt lands during PG's
startup sequence → `Connection refused`.

### The Fix

| # | What | Before (BUG) | After (FIX) |
|---|------|-------------|------------|
| 1 | DB hostname | `DB_HOST=localhost` | `DB_HOST=db` |
| 2 | Startup order | `depends_on: - db` (start only) | `depends_on: db: condition: service_healthy` |
| 3 | PG readiness | No healthcheck | `pg_isready` healthcheck on `db` service |
| 4 | DB port exposure | Exposed to host | Not exposed (internal network only) |

---

## Step-by-Step Guide (Git Bash)

### Step 0 — Clone / unzip and enter the project

```bash
cd middle_docker_network_fix
```

---

### Step 1 — Reproduce the bug ❌

```bash
# Use the buggy .env and buggy Compose file
cp .env.buggy .env

docker-compose -f docker-compose.buggy.yml up --build
```

Open a second terminal and test:

```bash
# Should return 503 with connection error details
curl -s http://localhost:8000/health/db | python -m json.tool
```

Expected response:
```json
{
  "status": "unhealthy",
  "host": "localhost",
  "error_type": "OperationalError",
  "error": "...",
  "hint": "If error contains 'Name or service not known'..."
}
```

Observe the startup warning in container logs:
```
⚠️  DB_HOST=localhost detected inside Docker! This will cause
    'Connection refused' or 'Name or service not known'.
    Set DB_HOST=db (the Docker service name) to fix.
```

Stop the buggy stack:
```bash
docker-compose -f docker-compose.buggy.yml down -v
```

---

### Step 2 — Apply the fix ✅

```bash
# Use the fixed .env
cp .env.example .env

# Start the fixed stack (default docker-compose.yml)
docker-compose up --build
```

Docker will now:
1. Start the `db` container
2. Wait for `pg_isready` to return success (healthcheck)
3. Only then start the `web` container

Test again:

```bash
# Should return 200 with healthy status
curl -s http://localhost:8000/health/db | python -m json.tool
```

Expected response:
```json
{
  "status": "healthy",
  "host": "db",
  "port": 5432,
  "database": "appdb",
  "query": "SELECT 1",
  "result": 1
}
```

Swagger UI: http://localhost:8000/docs

---

### Step 3 — Run unit tests (local, no Docker needed)

```bash
pip install -r requirements.txt
pytest tests/ -v
```

---

### Step 4 — Useful Docker commands

```bash
# Follow logs of the web service only
docker-compose logs -f web

# Check healthcheck status of the db container
docker inspect pg_debug_fixed | python -m json.tool | grep -A5 Health

# Connect to PostgreSQL directly (via docker exec, no host port needed)
docker exec -it pg_debug_fixed psql -U postgres -d appdb -c "SELECT version();"

# Tear down everything including volumes
docker-compose down -v
```

---

### Step 5 — Commit to Git

```bash
git init
git add .
git commit -m "fix: resolve docker networking issue between fastapi and postgres"

# Push to GitHub
git remote add origin https://github.com/YOUR_USER/middle_docker_network_fix.git
git push -u origin main
```

---

## Key Concepts for Middle Engineers

| Concept | Details |
|---------|---------|
| Docker DNS | Each service name in Compose is registered as a DNS entry on the shared network |
| `depends_on` condition | `service_healthy` waits for healthcheck; `service_started` (default) does not |
| `pg_isready` | Official PostgreSQL CLI probe — checks TCP + authentication readiness |
| `pool_pre_ping` | SQLAlchemy option that recycles stale connections transparently |
| Security | Never expose `db` port to the host in production — internal network only |
