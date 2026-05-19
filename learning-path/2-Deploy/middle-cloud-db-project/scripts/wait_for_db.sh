#!/usr/bin/env bash
# Helper: wait until PostgreSQL is accepting connections
# Usage: ./scripts/wait_for_db.sh
set -e

HOST="${DB_HOST:-db}"
PORT="${DB_PORT:-5432}"
USER="${DB_USER:-appuser}"

echo "⏳ Waiting for PostgreSQL at $HOST:$PORT …"
until pg_isready -h "$HOST" -p "$PORT" -U "$USER"; do
  sleep 2
done
echo "✅ PostgreSQL is ready"
