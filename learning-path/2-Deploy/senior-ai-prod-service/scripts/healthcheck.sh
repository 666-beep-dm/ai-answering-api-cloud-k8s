#!/usr/bin/env bash
set -e
echo "Checking service health…"
curl -sf http://localhost/health | python3 -m json.tool
echo "✅ Service is healthy"
