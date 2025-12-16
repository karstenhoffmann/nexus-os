#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source ./scripts/_fmt.sh

info "docker compose config (REDACTED)"

# Mask common secret env names
docker compose config | sed -E 's/([A-Z0-9_]*(_KEY|_TOKEN|_SECRET|_PASSWORD)):\s+.*/\1: REDACTED/g'

ok "Config ausgegeben (ohne Secrets)"
