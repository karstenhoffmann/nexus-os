#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source ./scripts/_fmt.sh

info "Preflight DEEP startet (Docker/Runtime/Native Checks)"

if [ "${PREVENT_CACHE:-0}" = "1" ]; then
  run "[1/4] Docker: build (no-cache)" docker compose build --no-cache
else
  run "[1/4] Docker: build" docker compose build
fi

run "[2/4] Container: Import Smoke Tests (python-multipart, sqlite-vec)" \
  docker compose run --rm app python -c "import multipart; import sqlite_vec; print('imports ok')"

run "[3/4] Container: sqlite-vec Load Test (ELF/arch faellt hier auf)" \
  docker compose run --rm app python -c "import sqlite3, sqlite_vec; conn=sqlite3.connect(':memory:'); sqlite_vec.load(conn); conn.execute('select 1'); print('sqlite-vec load ok')"

step "[4/4] Compose: redacted config (safe output)"; ./scripts/compose-config-redacted.sh >/dev/null; ok "[4/4] Compose: redacted config (safe output)"

ok "Preflight DEEP: alles gruen"
