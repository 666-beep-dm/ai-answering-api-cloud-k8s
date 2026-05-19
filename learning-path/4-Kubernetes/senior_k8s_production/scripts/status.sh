#!/usr/bin/env bash
# status.sh — cluster diagnostics
NAMESPACE="rag-system"

echo "===== All Resources ====="
kubectl get all -n "$NAMESPACE"

echo ""
echo "===== HPA Status ====="
kubectl get hpa -n "$NAMESPACE"
kubectl describe hpa rag-api-hpa -n "$NAMESPACE"

echo ""
echo "===== Pod Details ====="
kubectl describe pods -l app=rag-api -n "$NAMESPACE"

echo ""
echo "===== Recent Events ====="
kubectl get events -n "$NAMESPACE" --sort-by=.lastTimestamp | tail -20

echo ""
echo "===== Rolling Update History ====="
kubectl rollout history deployment/rag-api -n "$NAMESPACE"
