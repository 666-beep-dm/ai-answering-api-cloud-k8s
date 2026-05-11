#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# wait-for-db.sh — polls host:port until TCP connection succeeds.
# Usage: ./wait-for-db.sh <host> <port> [timeout_seconds]
# Example: ./wait-for-db.sh db 5432 30
# ─────────────────────────────────────────────────────────────────
set -e

HOST="${1:?Usage: $0 host port [timeout]}"
PORT="${2:?Usage: $0 host port [timeout]}"
TIMEOUT="${3:-30}"
ELAPSED=0

echo "⏳ Waiting for $HOST:$PORT (timeout: ${TIMEOUT}s)..."

until nc -z "$HOST" "$PORT" 2>/dev/null; do
    if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
        echo "❌ Timeout: $HOST:$PORT not available after ${TIMEOUT}s"
        exit 1
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

echo "✅ $HOST:$PORT is ready (waited ${ELAPSED}s)"
