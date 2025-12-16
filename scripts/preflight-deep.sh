#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Helper for colored output
function print_status {
  if [ "$1" == "ok" ]; then
    echo -e "\033[0;32m✅ $2\033[0m"
  elif [ "$1" == "error" ]; then
    echo -e "\033[0;31m❌ $2\033[0m"
  elif [ "$1" == "warn" ]; then
    echo -e "\033[0;33m⚠️ $2\033[0m"
  fi
}

echo "[1/4] Docker: build image (no cache optional via PREVENT_CACHE=1)"
if [ "${PREVENT_CACHE:-0}" = "1" ]; then
  docker compose build --no-cache
else
  docker compose build
fi
print_status ok "Docker image build completed."

echo "[2/4] Container: import smoke tests (python-multipart, sqlite-vec)"
docker compose run --rm app python -c "import multipart; import sqlite_vec; print('imports ok')"
print_status ok "Imported required packages."

echo "[3/4] Container: sqlite-vec load test (catches ELF/arch issues)"
docker compose run --rm app python -c "import sqlite3, sqlite_vec; conn=sqlite3.connect(':memory:'); sqlite_vec.load(conn); conn.execute('select 1'); print('sqlite-vec load ok')"
print_status ok "sqlite-vec loaded successfully."

echo "[4/4] Compose: show redacted config (optional debugging)"
./scripts/compose-config-redacted.sh >/dev/null
print_status ok "Config redacted and validated."

echo "✅ preflight-deep passed"
