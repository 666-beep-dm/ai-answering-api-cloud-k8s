# Middle-tier Cloud DB Project

Production-ready **FastAPI + PostgreSQL + Nginx** scaffold with full CRUD,
async database access, Docker Compose orchestration, and Nginx reverse proxy.

---

## Infrastructure Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM      | 2 GB    | **16 GB**   |
| CPU      | 2 vCPU  | 4 vCPU      |
| GPU VRAM | —       | **4 GB** (if ML workloads added) |
| Disk     | 20 GB SSD | 50 GB SSD |
| OS       | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

---

## Project Structure

```
middle-cloud-db-project/
├── app/
│   ├── __init__.py
│   ├── models.py        # SQLAlchemy 2.0 ORM models
│   ├── schemas.py       # Pydantic v2 request/response schemas
│   ├── crud.py          # Async CRUD operations
│   └── api/
│       ├── __init__.py
│       └── items.py     # FastAPI router (full CRUD)
├── nginx/
│   └── default.conf     # Reverse proxy config
├── scripts/
│   └── wait_for_db.sh
├── main.py              # App entry point + lifespan init
├── database.py          # Async engine, session factory, init_db()
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Quick Start (Local)

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env — set DB_PASSWORD and SECRET_KEY
```

### 2. Build & start all services

```bash
docker-compose up --build -d
```

### 3. Verify

```bash
curl http://localhost/health
# {"status": "ok"}

curl http://localhost/api/v1/items/
# {"total": 0, "items": []}
```

Interactive API docs: **http://localhost/docs**

---

## Git Workflow (Git Bash)

```bash
git init
git add .
git commit -m "feat: middle crud service with postgres"
```

---

## Deploy to Cloud VM (SSH)

### Step 1 — Connect to your VM

```bash
# AWS EC2
ssh -i ~/.ssh/your-key.pem ubuntu@<EC2_PUBLIC_IP>

# GCP / DigitalOcean
ssh root@<VM_PUBLIC_IP>
```

### Step 2 — Install Docker on the VM (Ubuntu 22.04)

```bash
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER && newgrp docker
```

### Step 3 — Copy project to VM

```bash
# From your local Git Bash:
zip -r middle_cloud_db_project.zip middle-cloud-db-project/
scp middle_cloud_db_project.zip ubuntu@<VM_IP>:~/
```

### Step 4 — Unzip & deploy

```bash
# On the VM:
unzip middle_cloud_db_project.zip
cd middle-cloud-db-project
cp .env.example .env
nano .env              # Set real passwords!
docker compose up --build -d
```

### Step 5 — Open firewall port 80

| Provider     | Action                                                    |
|-------------|-----------------------------------------------------------|
| AWS         | EC2 → Security Groups → Inbound → TCP 80 from 0.0.0.0/0  |
| GCP         | VPC Network → Firewall → Create Rule → tcp:80             |
| DigitalOcean | Networking → Firewalls → Inbound → TCP 80                |

> ⚠️ PostgreSQL port **5432 is never exposed** to the internet.  
> It is only reachable inside the private `backend` Docker network.

---

## API Endpoints

| Method | Path                   | Description        |
|--------|------------------------|--------------------|
| GET    | `/health`              | Health check       |
| GET    | `/api/v1/items/`       | List all items     |
| POST   | `/api/v1/items/`       | Create item        |
| GET    | `/api/v1/items/{id}`   | Get single item    |
| PATCH  | `/api/v1/items/{id}`   | Update item        |
| DELETE | `/api/v1/items/{id}`   | Delete item        |

---

## Security Notes

- Database has **no exposed ports** — only accessible via internal Docker network.
- Nginx adds security headers (`X-Content-Type-Options`, `X-Frame-Options`).
- All secrets live in `.env` which is listed in `.gitignore`.
- `X-Forwarded-For` / `X-Real-IP` headers are passed for accurate logging.
