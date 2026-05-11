#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────
# init-ssl.sh — One-time Let's Encrypt certificate bootstrap.
# Run ONCE on the VM after the first docker compose up.
#
# Usage: bash scripts/init-ssl.sh your-domain.com admin@your-domain.com
# ─────────────────────────────────────────────────────────────────────────
set -euo pipefail

DOMAIN="${1:?Provide domain, e.g.: bash init-ssl.sh example.com admin@example.com}"
EMAIL="${2:?Provide email for Let's Encrypt notifications}"

echo "▶ Issuing certificate for $DOMAIN (email: $EMAIL)"

docker compose -f docker-compose.prod.yml run --rm certbot certonly \
    --webroot \
    --webroot-path /var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN" \
    -d "www.$DOMAIN"

echo "▶ Reloading Nginx to pick up new cert..."
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload

echo "✅ SSL certificate issued for $DOMAIN"
echo "   Auto-renewal is handled by the certbot container (every 12h)."
