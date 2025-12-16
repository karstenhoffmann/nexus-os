#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/scripts/_fmt.sh"

info "Claude Session End"

if [ -f "$ROOT/STATE.md" ]; then
  step "Hinweis: Bitte Handoff in STATE.md aktualisieren, dann preflight + commit/push."
  ok "STATE.md vorhanden"
else
  warn "STATE.md fehlt (Handoff nicht moeglich)"
fi

step "Empfohlener Abschluss"
echo "1) ./scripts/preflight-fast.sh"
echo "2) git status"
echo "3) git add -A"
echo "4) git commit -m \"...\""
echo "5) git push"

ok "End-Hook fertig"
