#!/usr/bin/env bash
set -e
HOST="${1:?host required}"; PORT="${2:?port required}"; TIMEOUT="${3:-30}"
ELAPSED=0
echo "⏳ Waiting for $HOST:$PORT..."
until nc -z "$HOST" "$PORT" 2>/dev/null; do
    [ "$ELAPSED" -ge "$TIMEOUT" ] && echo "❌ Timeout after ${TIMEOUT}s" && exit 1
    sleep 1; ELAPSED=$((ELAPSED+1))
done
echo "✅ $HOST:$PORT ready (${ELAPSED}s)"
