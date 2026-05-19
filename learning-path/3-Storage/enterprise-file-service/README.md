# Enterprise File Service

Production-ready async file management microservice.
**FastAPI · PostgreSQL · Redis · S3-compatible storage · Docker**

---

## System Requirements

| Component | Specification         |
|-----------|-----------------------|
| CPU       | Intel i5-10300 / 4 cores |
| RAM       | 16 GB                 |
| GPU VRAM  | 4 GB (optional)       |
| Docker    | 24+                   |
| Python    | 3.10+                 |

---

## Architecture

```
Client
  │
  ▼
FastAPI (routers/)
  │
  ├── FileService (services/)        ← business logic
  │     ├── FileRepository (repositories/)  ← PostgreSQL via asyncpg
  │     └── S3Storage (storage/)            ← S3/MinIO via aioboto3
  │
  └── BackgroundTasks                ← async post-processing
```

See `docs/architecture.md` for full diagrams.

---

## Project Structure

```
enterprise-file-service/
├── src/
│   └── app/
│       ├── core/         config · exceptions · logging
│       ├── db/           async SQLAlchemy session
│       ├── models/       ORM models
│       ├── repositories/ DB queries
│       ├── routers/      FastAPI routes
│       ├── schemas/      Pydantic I/O models
│       ├── services/     business logic
│       ├── storage/      S3 client + retry
│       └── main.py
├── migrations/           Alembic
├── tests/                pytest (unit)
├── scripts/              shell helpers
├── docs/                 architecture notes
├── .env.example
├── alembic.ini
├── Dockerfile            multi-stage
├── docker-compose.yml    api + db + redis (+ minio profile)
└── requirements*.txt
```

---

## Quick Start (Git Bash)

### 1 · Clone & initialise

```bash
git init
git add .
git commit -m "feat: enterprise file service — initial commit"
# Add your remote:
git remote add origin https://github.com/<your-org>/enterprise-file-service.git
git push -u origin main
```

### 2 · Configure environment

```bash
cp .env.example .env
# Edit .env — set real DB/S3/Redis credentials
```

### 3 · Build & run (with local MinIO)

```bash
docker-compose --profile dev up --build
```

| Service      | URL                          |
|--------------|------------------------------|
| API          | http://localhost:8000        |
| Swagger UI   | http://localhost:8000/docs   |
| MinIO console| http://localhost:9001        |

### 4 · Run database migrations

```bash
docker-compose exec api alembic upgrade head
# or from host:
# DB_HOST=localhost alembic upgrade head
```

### 5 · Run tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## API Reference

| Method | Path                          | Description                      |
|--------|-------------------------------|----------------------------------|
| POST   | /api/v1/files/upload          | Server-side file upload          |
| POST   | /api/v1/files/upload/presigned| Get presigned PUT URL            |
| GET    | /api/v1/files/{id}/download   | Get presigned GET URL            |
| GET    | /api/v1/files/                | List all file records            |
| GET    | /health                       | Health check                     |

---

## Error Reference

| HTTP | Exception                 | Cause                                |
|------|---------------------------|--------------------------------------|
| 401  | `S3AuthError`             | Invalid credentials                  |
| 404  | `FileRecordNotFoundError` | DB record missing                    |
| 404  | `StorageKeyNotFoundError` | S3 key missing                       |
| 413  | `FileTooLargeError`       | Exceeds `MAX_FILE_SIZE_MB`           |
| 415  | `InvalidMimeTypeError`    | MIME not in allow-list               |
| 502  | `S3UploadError`           | S3 put_object failed after retries   |
| 503  | `BucketUnavailableError`  | Bucket unreachable                   |

---

## Stopping

```bash
docker-compose down          # stop containers
docker-compose down -v       # stop + remove volumes (⚠ deletes data)
```
