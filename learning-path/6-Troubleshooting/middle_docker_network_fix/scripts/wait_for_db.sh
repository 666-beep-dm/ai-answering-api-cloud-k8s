#!/usr/bin/env bash
# scripts/wait_for_db.sh
# Fallback wait script (used when Docker healthcheck is not available).
# In the fixed docker-compose.yml the healthcheck + depends_on handles this.

set -e

HOST="${DB_HOST:-db}"
PORT="${DB_PORT:-5432}"
TIMEOUT=60
INTERVAL=2
ELAPSED=0

echo "[wait_for_db] Waiting for PostgreSQL at ${HOST}:${PORT} ..."

until pg_isready -h "$HOST" -p "$PORT" -U "${DB_USER:-postgres}" > /dev/null 2>&1; do
  if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
    echo "[wait_for_db] ❌ Timed out after ${TIMEOUT}s waiting for PostgreSQL"
    exit 1
  fi
  echo "[wait_for_db] ⏳ Not ready yet — retrying in ${INTERVAL}s (${ELAPSED}s elapsed)"
  sleep "$INTERVAL"
  ELAPSED=$((ELAPSED + INTERVAL))
done

echo "[wait_for_db] ✅ PostgreSQL is ready!"
exec "$@"
