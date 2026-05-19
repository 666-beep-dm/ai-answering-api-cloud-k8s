#!/usr/bin/env bash
# deploy.sh — full local deployment helper
set -euo pipefail

NAMESPACE="rag-system"
IMAGE="my-rag-api:latest"

echo "==> [1/5] Building Docker image..."
docker build -t "$IMAGE" .

echo "==> [2/5] Loading image into local cluster..."
# Uncomment the line matching your local cluster:
minikube image load "$IMAGE"
# kind load docker-image "$IMAGE"

echo "==> [3/5] Creating namespace (idempotent)..."
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

echo "==> [4/5] Applying manifests in dependency order..."
kubectl apply -f k8s/base/namespace.yaml
kubectl apply -f k8s/base/configmap.yaml
kubectl apply -f k8s/base/secret.yaml
kubectl apply -f k8s/base/db.yaml
kubectl apply -f k8s/base/redis.yaml

echo "    Waiting for PostgreSQL to become ready..."
kubectl rollout status deployment/postgres -n "$NAMESPACE" --timeout=120s

echo "    Waiting for Redis to become ready..."
kubectl rollout status deployment/redis -n "$NAMESPACE" --timeout=60s

kubectl apply -f k8s/base/api.yaml
kubectl apply -f k8s/base/network.yaml

echo "==> [5/5] Deployment complete. Checking status..."
kubectl get all -n "$NAMESPACE"

echo ""
echo "Access the API:"
echo "  minikube: curl http://\$(minikube ip):30080/health"
echo "  or add to /etc/hosts: <minikube-ip> rag.local, then curl http://rag.local/health"
