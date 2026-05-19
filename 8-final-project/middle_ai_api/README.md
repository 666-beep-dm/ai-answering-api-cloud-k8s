# Middle-tier AI Answering API

> RAG-powered Q&A microservice — FastAPI · FAISS · sentence-transformers · GPT-4o-mini · S3

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        Client                           │
└────────────┬────────────────────────┬───────────────────┘
             │ POST /upload           │ POST /ask
             ▼                        ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI (app/main.py)                   │
│   middleware: JSON logging · global error handler        │
└────────────┬────────────────────────┬───────────────────┘
             │                        │
    ┌────────▼────────┐    ┌──────────▼──────────┐
    │   s3_service    │    │     rag_service      │
    │  (aioboto3)     │    │  FAISS + embeddings  │
    │  exponential    │    │  recursive splitter  │
    │  retry logic    │    │  top-k retrieval     │
    └────────┬────────┘    └──────────┬──────────┘
             │                        │
    ┌────────▼────────┐    ┌──────────▼──────────┐
    │  S3-compatible  │    │     llm_service      │
    │  bucket (R2 /   │    │  AsyncOpenAI retry   │
    │  AWS / Selectel)│    │  anti-hallucination  │
    └─────────────────┘    │  prompt engineering  │
                           └─────────────────────┘
```

---

## Recommended Hardware

| Resource | Minimum |
|----------|---------|
| RAM      | 16 GB   |
| CPU      | 4 cores |
| Disk     | 10 GB   |
| Docker   | 24+     |

---

## Environment Variables

| Variable              | Default                              | Description                          |
|-----------------------|--------------------------------------|--------------------------------------|
| `OPENAI_API_KEY`      | —                                    | Your OpenAI API key                  |
| `OPENAI_MODEL`        | `gpt-4o-mini`                        | Chat completion model                |
| `USE_MOCK`            | `false`                              | Skip real API calls (dev/test)       |
| `S3_ENDPOINT_URL`     | *(empty = real AWS)*                 | Override for R2 / MinIO / Selectel   |
| `S3_ACCESS_KEY_ID`    | —                                    | S3 access key                        |
| `S3_SECRET_ACCESS_KEY`| —                                    | S3 secret key                        |
| `S3_BUCKET_NAME`      | `ai-answering-api`                   | Target bucket                        |
| `S3_REGION`           | `us-east-1`                          | AWS region (ignored by some providers)|
| `VECTOR_DB_PATH`      | `./vector_db`                        | FAISS index storage path             |
| `CHUNK_SIZE`          | `512`                                | Max chars per chunk                  |
| `CHUNK_OVERLAP`       | `64`                                 | Overlap between consecutive chunks  |
| `TOP_K_CHUNKS`        | `3`                                  | Chunks returned per query            |
| `EMBEDDING_MODEL`     | `sentence-transformers/all-MiniLM-L6-v2` | HuggingFace embedding model      |
| `MAX_FILE_SIZE_MB`    | `10`                                 | Upload size limit                    |
| `LOG_LEVEL`           | `INFO`                               | Python log level                     |
| `LOG_DIR`             | `./logs`                             | Directory for log files              |

---

## Quick Start (Git Bash)

### 1 · Configure environment

```bash
cp .env.example .env
# Fill in OPENAI_API_KEY and S3 credentials in .env
# For local testing without an API key, set USE_MOCK=true
```

### 2 · Initialise Git repository

```bash
git init
git add .
git commit -m "feat: implement middle-tier RAG API with S3 storage"
```

### 3 · Build & run

```bash
docker-compose up --build -d
```

### 4 · Upload a document

```bash
curl -X POST http://localhost:8000/upload \
     -F "file=@/c/Users/you/my_document.txt"
```

### 5 · Ask a question

```bash
curl -X POST http://localhost:8000/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "What is the main topic of the uploaded document?"}'
```

Expected response:
```json
{
  "answer": "According to the document, the main topic is ...",
  "source_chunks_used": 3
}
```

### 6 · Health check

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "s3_connected": true,
  "vector_index_ready": true,
  "indexed_chunks": 42
}
```

### 7 · Interactive API docs

Open **http://localhost:8000/docs** in your browser.

### 8 · Stop the service

```bash
docker-compose down
```

---

## Push to GitHub

```bash
git remote add origin https://github.com/<your-username>/<repo-name>.git
git branch -M main
git push -u origin main
```

---

## Supported File Types

| Extension | Notes                                |
|-----------|--------------------------------------|
| `.txt`    | Full UTF-8 text extraction           |
| `.pdf`    | Text-layer extraction via `pypdf`    |

---

## Resilience Features

- **S3 uploads** — exponential backoff, up to 3 retries
- **OpenAI calls** — exponential backoff, up to 3 retries
- **Anti-hallucination prompt** — LLM is instructed to answer only from retrieved context
- **Docker** — `restart: unless-stopped` auto-recovers crashed containers
- **FAISS persistence** — index survives container restarts via Docker volume
