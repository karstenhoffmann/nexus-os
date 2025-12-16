#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/scripts/_fmt.sh"

info "Claude Session Start"

if [ -f "$ROOT/STATE.md" ]; then
  step "STATE.md (kurz)"
  # erste ~40 Zeilen reichen als Einstieg
  sed -n '1,40p' "$ROOT/STATE.md" || true
  ok "STATE.md geladen"
else
  warn "STATE.md fehlt"
fi

ok "Start-Hook fertig"
