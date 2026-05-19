# middle-k8s-project

Production-style FastAPI service with ConfigMap, Secret, Deployment (3 replicas), and NodePort Service — designed for local Kubernetes (minikube / Docker Desktop).

---

## Hardware Requirements

| Component | Recommended                  |
|-----------|------------------------------|
| RAM       | 16 GB                        |
| CPU       | 4 cores (e.g. Intel i5-10300H) |
| Disk      | 20 GB free                   |
| OS        | Windows 10/11, macOS, Linux  |

> With 3 replicas and probes enabled, at least 8 GB free RAM is needed for a stable local cluster.

---

## Project Structure

```
middle_k8s_project/
├── app/
│   ├── main.py              # FastAPI app — reads APP_COLOR, DATABASE_PASSWORD
│   └── requirements.txt
├── k8s/
│   ├── configmap.yaml       # Non-sensitive config (APP_ENV, APP_COLOR)
│   ├── secret.yaml          # Base64-encoded secrets (DATABASE_PASSWORD)
│   ├── deployment.yaml      # 3 replicas, probes, resource limits, non-root
│   └── service.yaml         # NodePort → localhost:30080
├── Dockerfile               # Multi-stage build, non-root user
├── .gitignore
└── README.md
```

---

## Step-by-Step Guide (Git Bash / Terminal)

### 1. Build the Docker image

```bash
docker build -t my-fastapi-app:latest .
```

### 2. Load image into local cluster

**minikube:**
```bash
minikube image load my-fastapi-app:latest
```

**kind:**
```bash
kind load docker-image my-fastapi-app:latest
```

**Docker Desktop:** image is already available — no extra step needed.

### 3. Validate manifests (no cluster required)

```bash
kubectl apply -f k8s/ --dry-run=client
```

### 4. Apply manifests — order matters

```bash
# ConfigMap and Secret must exist before Deployment reads them
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Or apply the whole folder (kubectl resolves dependencies automatically)
kubectl apply -f k8s/
```

### 5. Diagnostics

```bash
# Overview of all resources
kubectl get all

# Pod list with status
kubectl get pods -l app=fastapi-app

# Detailed pod info (events, probes, env)
kubectl describe pod -l app=fastapi-app

# Live logs
kubectl logs -l app=fastapi-app --follow

# Check environment inside a running pod
kubectl exec -it <pod-name> -- env | grep APP
```

### 6. Test the endpoint

```bash
# Docker Desktop / kind
curl http://localhost:30080/health

# minikube
curl http://$(minikube ip):30080/health
```

Expected: `{"status":"ok","env":"production","color":"green","db_password_set":true}`

### 7. Tear down

```bash
kubectl delete -f k8s/
```

---

## Git Workflow

```bash
git init
git add .
git commit -m "feat: middle-tier k8s infrastructure"
```

---

## Security Notes

| Practice | Implementation |
|---|---|
| Non-root container | `runAsUser: 1000`, `runAsNonRoot: true` |
| No privilege escalation | `allowPrivilegeEscalation: false` |
| Read-only filesystem | `readOnlyRootFilesystem: true` + `/tmp` emptyDir |
| Drop all Linux capabilities | `capabilities.drop: [ALL]` |
| Secrets not in image | Injected at runtime via `secretKeyRef` |

> ⚠️  `secret.yaml` uses base64 encoding, which is **not** encryption.  
> For real production use, consider **Sealed Secrets** or **HashiCorp Vault**.

---

## Resource Budget (per pod)

| | Request | Limit  |
|---|---------|--------|
| CPU    | 50m  | 100m   |
| Memory | 64Mi | 128Mi  |

3 replicas × 100m = **300m CPU** and 3 × 128Mi = **384Mi RAM** maximum cluster usage.
