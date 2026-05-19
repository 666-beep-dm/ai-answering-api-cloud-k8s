# File Upload Service

Async REST microservice for uploading files, built with **FastAPI** + **Docker**.

---

## System Requirements

| Resource | Minimum |
|----------|---------|
| RAM      | 16 GB   |
| GPU VRAM | 4 GB    |
| CPU      | 4 cores |
| Docker   | 24+     |
| Python   | 3.10+   |

---

## Project Structure

```
file-upload-service/
├── app/
│   ├── __init__.py
│   └── main.py          # FastAPI application
├── uploads/             # Persisted file storage (mounted volume)
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Quick Start (Git Bash / Linux / macOS)

### 1. Clone & initialise repository

```bash
git init
git add .
git commit -m "feat: initial file upload service"
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env if you need a different port
```

### 3. Build & run with Docker Compose

```bash
docker-compose up --build
```

The service will be available at **http://localhost:8000**.

### 4. Interactive API docs

Open **http://localhost:8000/docs** in your browser (Swagger UI).

---

## API Reference

### `POST /upload`

Upload a file via `multipart/form-data`.

**Request**

```
Content-Type: multipart/form-data
Body: file=<binary>
```

**Response `201 Created`**

```json
{
  "filename": "3f2a1b...uuid...ext",
  "original_filename": "report.pdf",
  "status": "uploaded"
}
```

**cURL example**

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@/path/to/your/file.pdf"
```

### `GET /health`

Returns `{"status": "ok"}` — useful for container health checks.

---

## Development (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## Stopping the service

```bash
docker-compose down          # stop containers
docker-compose down -v       # stop + remove volumes (deletes uploads!)
```
