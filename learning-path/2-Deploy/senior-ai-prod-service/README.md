# Senior AI Production RAG Service

Production-ready **FastAPI + LangChain + PostgreSQL + Redis + Nginx** scaffold
for a Retrieval-Augmented Generation AI service, following **Clean Architecture**
and **12-Factor App** principles.

---

## Infrastructure Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU      | 2 cores | **4+ cores** |
| RAM      | 4 GB    | **16 GB**    |
| GPU VRAM | —       | **4 GB** (NVIDIA, for local embeddings) |
| Disk     | 20 GB SSD | 100 GB SSD |
| OS       | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| Docker   | 24+     | 26+          |

---

## Architecture Diagram

```
 Client ──HTTPS──► Nginx :443 ──► FastAPI API :8000
                                      │
                  ┌───────────────────┤ (backend-only network)
                  │                   │
            PostgreSQL             Redis
           (history log)        (semantic cache)
                  │
           FAISS VectorStore ──► OpenAI LLM (streaming)
```

Full diagram: [docs/architecture.md](docs/architecture.md)

---

## Quick Start (Local)

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env: set OPENAI_API_KEY, DB_PASSWORD, SECRET_KEY

# 2. Build & start all services
docker-compose up --build -d

# 3. Ingest documents (optional)
docker-compose exec api python scripts/ingest.py --source docs/

# 4. Test the RAG endpoint
curl -X POST http://localhost/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this service about?", "stream": false}'

# 5. Interactive docs (dev mode only)
open http://localhost/docs

# 6. Metrics
curl http://localhost/metrics
```

---

## Git Bash Setup Guide

### Step 1 — Generate SSH key for VM access

```bash
ssh-keygen -t ed25519 -C "deploy@your-project" -f ~/.ssh/deploy_key
cat ~/.ssh/deploy_key.pub
# Add this public key to your VM's ~/.ssh/authorized_keys
```

### Step 2 — Add GitHub Actions Secrets

Go to: **GitHub repo → Settings → Secrets and variables → Actions**

| Secret Name   | Value                                      |
|---------------|--------------------------------------------|
| `VM_HOST`     | Your VM's public IP or domain              |
| `VM_USER`     | SSH username (e.g. `ubuntu`)               |
| `VM_SSH_KEY`  | Contents of `~/.ssh/deploy_key` (private)  |
| `GHCR_TOKEN`  | GitHub Personal Access Token (write:packages) |

### Step 3 — Init git and push

```bash
cd senior-ai-prod-service
git init
git add .
git commit -m "feat: senior AI production RAG service"
git branch -M main
git remote add origin https://github.com/<your-org>/<your-repo>.git
git push -u origin main
# ↑ This triggers the CI/CD pipeline automatically
```

---

## Deploy to Cloud VM

### Initial VM setup (one-time)

```bash
ssh ubuntu@<VM_IP>

# Install Docker
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER && newgrp docker

# Create app directory
mkdir -p ~/app
```

### Manual deploy

```bash
# From local Git Bash — copy project
zip -r senior_ai_prod_service.zip senior-ai-prod-service/
scp senior_ai_prod_service.zip ubuntu@<VM_IP>:~/
ssh ubuntu@<VM_IP> "unzip senior_ai_prod_service.zip && \
  cd senior-ai-prod-service && cp .env.example .env && \
  nano .env"  # Fill real secrets!

# On VM
cd senior-ai-prod-service
docker compose up --build -d
```

### SSL with Let's Encrypt

```bash
# On VM — issue certificate (replace with your real domain)
docker compose run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d yourdomain.com -d www.yourdomain.com \
  --email your@email.com --agree-tos --non-interactive

# Then uncomment the HTTPS server block in infra/nginx/conf.d/default.conf
docker compose exec nginx nginx -s reload
```

### GPU support (local embeddings)

```bash
# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list \
  | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# Then uncomment the GPU section in docker-compose.yaml
```

---

## CI/CD Pipeline (GitHub Actions)

Triggered on every push to `main`:

1. **Lint** — `ruff check` + `ruff format`
2. **Build** — Multi-stage Docker image → push to GHCR
3. **Deploy** — SSH → `docker compose pull` → rolling `--scale api=2` restart

---

## Observability

| Tool       | Endpoint              | Purpose                     |
|------------|-----------------------|-----------------------------|
| Prometheus | `GET /metrics`        | Latency, cache hit rate, etc |
| JSON logs  | stdout (Docker logs)  | Structured, Loki-compatible  |
| Health     | `GET /health`         | App + DB check               |
| Readiness  | `GET /readiness`      | DB + Redis check             |

---

## Security Notes

- PostgreSQL and Redis are on an `internal: true` Docker network — **never exposed to the internet**
- API docs disabled in `production` env
- Secrets injected via `.env` (never committed — in `.gitignore`)
- Nginx adds security headers on all responses
