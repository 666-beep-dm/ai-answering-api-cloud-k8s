# senior-k8s-production — RAG Microservice Platform

Production-grade Kubernetes infrastructure for a **RAG (Retrieval-Augmented Generation)**  
application: FastAPI API + PostgreSQL + Redis, isolated in namespace `rag-system`.

---

## Architecture

```
                        Internet
                           │
                    ┌──────▼───────┐
                    │ Nginx Ingress│  rag.local
                    └──────┬───────┘
                           │ :80
                    ┌──────▼───────┐        ┌───────────────┐
                    │  rag-api     │◄──────►│  redis-svc    │
                    │  (HPA 2-6)   │  cache  │  :6379        │
                    └──────┬───────┘        └───────────────┘
                           │ asyncpg
                    ┌──────▼───────┐
                    │  postgres-svc│
                    │  :5432       │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  PVC 5Gi     │  (postgres-pvc)
                    └──────────────┘
```

---

## Infrastructure Requirements

| Component | Recommended                        |
|-----------|------------------------------------|
| RAM       | 16 GB                              |
| CPU       | 4+ cores (e.g. Intel i5-10300H)    |
| GPU       | 4 GB VRAM (optional, for local LLM)|
| Disk      | 40 GB free SSD                     |
| OS        | Windows 10/11 + WSL2, macOS, Linux |

> minikube: allocate at least 4 CPU and 6 GB RAM to the cluster:  
> `minikube start --cpus=4 --memory=6144`

---

## Resource Budget

| Service    | CPU request | CPU limit | RAM request | RAM limit |
|------------|-------------|-----------|-------------|-----------|
| rag-api ×2 | 2 × 100m    | 2 × 500m  | 2 × 128Mi   | 2 × 256Mi |
| postgres   | 200m        | 500m      | 256Mi       | 512Mi     |
| redis      | 50m         | 200m      | 64Mi        | 128Mi     |
| **Total**  | **450m**    | **1.7**   | **576Mi**   | **1.1Gi** |

---

## Project Structure

```
senior_k8s_production/
├── app/
│   ├── main.py                     # FastAPI — /health + /ask (asyncpg + aioredis)
│   └── requirements.txt
├── k8s/
│   ├── base/
│   │   ├── namespace.yaml          # Namespace: rag-system
│   │   ├── configmap.yaml          # Non-sensitive config
│   │   ├── secret.yaml             # base64 secrets
│   │   ├── db.yaml                 # Postgres PVC + Deployment + Service
│   │   ├── redis.yaml              # Redis PVC + Deployment + Service
│   │   ├── api.yaml                # FastAPI Deployment + ClusterIP Service
│   │   └── network.yaml            # Ingress + HPA + NetworkPolicy
│   └── overlays/
│       └── local/
│           └── kustomization.yaml  # Kustomize patch (1 replica for laptop)
├── scripts/
│   ├── deploy.sh                   # Full deployment helper
│   └── status.sh                   # Diagnostics helper
├── Dockerfile                      # Multi-stage, non-root
├── .gitignore
└── README.md
```

---

## Step-by-Step Guide (Git Bash / Terminal)

### 0. Enable Nginx Ingress (minikube)

```bash
minikube addons enable ingress
minikube addons enable metrics-server   # required for HPA
```

### 1. Build & load Docker image

```bash
docker build -t my-rag-api:latest .

# minikube:
minikube image load my-rag-api:latest

# kind:
kind load docker-image my-rag-api:latest
```

### 2. Create namespace

```bash
kubectl create namespace rag-system
```

### 3. Apply manifests (dependency order)

```bash
kubectl apply -f k8s/base/namespace.yaml
kubectl apply -f k8s/base/configmap.yaml
kubectl apply -f k8s/base/secret.yaml
kubectl apply -f k8s/base/db.yaml
kubectl apply -f k8s/base/redis.yaml

# Wait for storage to be ready
kubectl rollout status deployment/postgres -n rag-system
kubectl rollout status deployment/redis    -n rag-system

kubectl apply -f k8s/base/api.yaml
kubectl apply -f k8s/base/network.yaml
```

Or use the helper script:

```bash
bash scripts/deploy.sh
```

### 4. Validate without a cluster (dry-run)

```bash
kubectl apply -f k8s/base/ --dry-run=client
```

### 5. Diagnostics

```bash
# All resources in namespace
kubectl get all -n rag-system

# Pod-level details & events
kubectl describe pod -l app=rag-api -n rag-system

# Live logs
kubectl logs -l app=rag-api -n rag-system --follow

# Check HPA scaling status
kubectl get hpa -n rag-system
kubectl describe hpa rag-api-hpa -n rag-system

# Watch rolling update in real time
kubectl rollout status deployment/rag-api -n rag-system
kubectl rollout history deployment/rag-api -n rag-system

# Rollback if needed
kubectl rollout undo deployment/rag-api -n rag-system
```

### 6. Test endpoints

```bash
# Add to /etc/hosts (or C:\Windows\System32\drivers\etc\hosts):
# $(minikube ip) rag.local

curl http://rag.local/health
curl -X POST http://rag.local/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "What is RAG?"}'
```

### 7. Kustomize overlay (local — 1 replica)

```bash
kubectl apply -k k8s/overlays/local/
```

### 8. Tear down

```bash
kubectl delete namespace rag-system
```

---

## Git Workflow

```bash
git init
git add .
git commit -m "feat: senior production-grade k8s setup"
```

---

## Security Highlights

| Control                     | Implementation                              |
|-----------------------------|---------------------------------------------|
| Non-root containers         | `runAsNonRoot: true`, `runAsUser: 1000`     |
| No privilege escalation     | `allowPrivilegeEscalation: false`           |
| Read-only root filesystem   | `readOnlyRootFilesystem: true` + `/tmp` emptyDir |
| Drop all Linux capabilities | `capabilities.drop: [ALL]`                  |
| Network isolation           | `NetworkPolicy` — explicit ingress/egress   |
| Secrets not baked into image| Runtime injection via `secretKeyRef`        |
| Init containers             | Prevent API starting before DB/Redis ready  |

---

## HPA Scaling Thresholds

| Metric | Scale-out threshold | Min replicas | Max replicas |
|--------|---------------------|--------------|--------------|
| CPU    | 65% average         | 2            | 6            |
| Memory | 75% average         | 2            | 6            |
