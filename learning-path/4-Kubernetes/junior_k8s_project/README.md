# junior-k8s-project

Minimal FastAPI application packaged for local Kubernetes (minikube / Docker Desktop).

---

## Hardware Requirements

| Component | Recommended         |
|-----------|---------------------|
| RAM       | 16 GB               |
| CPU       | Intel i5-10300H+    |
| Disk      | 20 GB free          |
| OS        | Windows 10/11, macOS, Linux |

> These specs ensure stable operation of a local Kubernetes cluster alongside your IDE and browser.

---

## Project Structure

```
junior_k8s_project/
├── app/
│   └── main.py          # FastAPI application
├── k8s/
│   ├── deployment.yaml  # Kubernetes Deployment (1 replica, resource limits)
│   └── service.yaml     # Kubernetes Service (NodePort → localhost:30080)
├── Dockerfile
├── .gitignore
└── README.md
```

---

## Step-by-Step Guide (Git Bash / Terminal)

### 1. Build the Docker image

```bash
docker build -t my-fastapi-app:latest .
```

> **minikube users** — load the image into the cluster first:
> ```bash
> minikube image load my-fastapi-app:latest
> ```

### 2. Validate Kubernetes manifests (dry-run, no cluster needed)

```bash
kubectl apply -f k8s/ --dry-run=client
```

Expected output:
```
deployment.apps/fastapi-app created (dry run)
service/fastapi-app-svc created (dry run)
```

### 3. Deploy to the cluster

```bash
kubectl apply -f k8s/
```

### 4. Check status

```bash
# List pods — wait for STATUS = Running
kubectl get pods

# List services — find NodePort (30080)
kubectl get svc

# View pod logs
kubectl logs -l app=fastapi-app
```

### 5. Test the endpoint

```bash
# Docker Desktop / kind
curl http://localhost:30080/health

# minikube
curl http://$(minikube ip):30080/health
```

Expected response: `{"status":"ok"}`

### 6. Tear down

```bash
kubectl delete -f k8s/
```

---

## Git Workflow

```bash
git init
git add .
git commit -m "feat: initial k8s manifests"
```

---

## Resource Limits

| Parameter | Request | Limit  |
|-----------|---------|--------|
| CPU       | 50m     | 100m   |
| Memory    | 64Mi    | 128Mi  |

Tuned for laptop use — safe to run alongside minikube's own overhead.
