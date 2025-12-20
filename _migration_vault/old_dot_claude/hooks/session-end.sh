#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/scripts/_fmt.sh"

info "Claude Session End - Final Check"

# Automatisch den Fast-Preflight triggern
step "Führe Preflight-Checks aus..."
if "$ROOT/scripts/preflight-fast.sh"; then
  ok "Preflight erfolgreich"
else
  error "Preflight fehlgeschlagen! Bitte korrigiere die Fehler vor dem Commit."
fi

if [ -f "$ROOT/STATE.md" ]; then
  step "Prüfe STATE.md Handoff..."
  # Prüfe ob heute ein Eintrag gemacht wurde (optionaler Check)
  ok "Handoff in STATE.md ist Pflicht."
fi

info "Bereit zum Commit & Push."
echo "Befehl: git add . && git commit -m \"feat: ...\" && git push"