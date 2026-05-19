# S3 Integration Service

Async FastAPI microservice for uploading files and generating presigned URLs
for any S3-compatible object storage — **AWS S3**, **Selectel**, **MinIO**.

---

## Hardware Requirements

| Resource | Minimum  |
|----------|----------|
| RAM      | 16 GB    |
| CPU      | 4 cores  |
| Docker   | 24+      |
| Python   | 3.10+    |

---

## Project Structure

```
s3-integration-service/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py          # FastAPI router
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py          # pydantic-settings
│   │   ├── exceptions.py      # custom HTTP exceptions
│   │   └── logging.py         # structured logging setup
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── file.py            # Pydantic request/response models
│   ├── services/
│   │   ├── __init__.py
│   │   └── s3_service.py      # S3Service (aioboto3)
│   ├── __init__.py
│   └── main.py
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
# Fill in your real S3 credentials
```

### 2. Git initialisation (Git Bash)

```bash
git init
git add .
git commit -m "feat: s3 integration service"
```

### 3. Run with Docker Compose

```bash
docker-compose up --build
```

Service: **http://localhost:8000**
Swagger UI: **http://localhost:8000/docs**

### 4. Local development with MinIO (optional)

```bash
docker-compose --profile dev up --build
```

MinIO console: **http://localhost:9001** (user: `minioadmin` / pass: `minioadmin`)

---

## API Reference

### `POST /api/v1/files/upload`

Upload a file (≤10 MB, allowed MIME types: jpeg/png/gif/webp/pdf/txt/csv/zip/json).

```bash
curl -X POST http://localhost:8000/api/v1/files/upload \
  -F "file=@photo.jpg"
```

**Response `201`**

```json
{
  "filename": "3f2a1b..._photo.jpg",
  "original_filename": "photo.jpg",
  "size_bytes": 204800,
  "mime_type": "image/jpeg",
  "status": "uploaded"
}
```

### `GET /api/v1/files/{filename}`

Get a presigned URL (default TTL: 3600 s).

```bash
curl http://localhost:8000/api/v1/files/3f2a1b..._photo.jpg
```

**Response `200`**

```json
{
  "filename": "3f2a1b..._photo.jpg",
  "url": "https://...",
  "expires_in_seconds": 3600
}
```

---

## Error Reference

| HTTP | Exception              | Trigger                              |
|------|------------------------|--------------------------------------|
| 401  | `S3AuthError`          | Invalid credentials                  |
| 404  | `FileNotFoundInStorage`| File key absent in bucket            |
| 413  | `FileTooLargeError`    | File exceeds `MAX_FILE_SIZE_MB`      |
| 415  | `InvalidMimeTypeError` | MIME type not in allow-list          |
| 503  | `BucketUnavailableError`| Bucket missing or unreachable       |

---

## Stop the service

```bash
docker-compose down          # stop containers
docker-compose down -v       # stop + remove volumes
```
