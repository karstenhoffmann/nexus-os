#!/usr/bin/env bash
set -euo pipefail

echo "=== where am I ==="
pwd
id || true
uname -a || true
cat /etc/os-release 2>/dev/null || true

echo ""
echo "=== tools ==="
command -v node >/dev/null 2>&1 && node -v || echo "NO_NODE"
command -v npx  >/dev/null 2>&1 && npx -v  || echo "NO_NPX"
command -v curl >/dev/null 2>&1 && curl --version | head -n 1 || echo "NO_CURL"

echo ""
echo "=== host reachability ==="
# 1) try docker-style host alias
curl -I -sS http://host.docker.internal:8000/ | head -n 5 || echo "NO_HTTP_host.docker.internal"

# 2) try common default gateway IP (works in many container setups)
curl -I -sS http://172.17.0.1:8000/ | head -n 5 || echo "NO_HTTP_172.17.0.1"

# 3) show route table for debugging
echo ""
echo "=== routing ==="
ip route 2>/dev/null || true
