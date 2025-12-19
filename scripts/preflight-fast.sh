#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source ./scripts/_fmt.sh

info "🚀 Nexus-OS Preflight FAST (Sicherheits- & Test-Check)"

# --- TEIL 1: STATISCHE GUARDRAILS (Deine bewährten Checks) ---

run "[1/6] YAML: docker-compose.yml hat keine Tabs" bash -lc '
  if grep -n $'"'"'\t'"'"' docker-compose.yml >/dev/null 2>&1; then
    echo "Tabs gefunden:"
    grep -n $'"'"'\t'"'"' docker-compose.yml || true
    exit 1
  fi
'

run "[2/6] YAML: docker compose config validiert" docker compose config >/dev/null

run "[3/6] Docs: kein Copy-Paste Artefakt \\_local" bash -lc '
  if grep -R --line-number "\\\\_local" README.md .gitignore docker-compose.yml >/dev/null 2>&1; then
    echo "Gefunden (bitte _local ohne Backslash verwenden):"
    grep -R --line-number "\\\\_local" README.md .gitignore docker-compose.yml || true
    exit 1
  fi
'

run "[4/6] Code: keine Markdown Artefakte (**future**, **file**) in Python" bash -lc '
  if grep -R --line-number -E "\\*\\*future\\*\\*|\\*\\*file\\*\\*" app --include="*.py" >/dev/null 2>&1; then
    echo "Gefunden (das ist kaputter Copy-Paste aus Markdown):"
    grep -R --line-number -E "\\*\\*future\\*\\*|\\*\\*file\\*\\*" app --include="*.py" || true
    exit 1
  fi
'

# --- TEIL 2: LOGIK & TESTS (Die neue Struktur) ---

step "[5/6] Backend: Python Syntax & Tests"
# Lokaler Syntax Check
PYBIN=""
if command -v python3 >/dev/null 2>&1; then PYBIN="python3"; fi
if command -v python  >/dev/null 2>&1; then PYBIN="python";  fi
if [ -n "$PYBIN" ]; then
  "$PYBIN" -m compileall -q app
  ok "Syntax-Compile sauber"
fi

# Ausführung der Backend-Tests im neuen Ordner (via Docker)
if [ -d "tests/backend" ]; then
    info "Führe Backend-Tests in tests/backend aus..."
    docker compose exec -T app pytest tests/backend
    ok "Backend-Tests bestanden"
else
    warn "Keine Backend-Tests in tests/backend gefunden!"
fi

step "[6/6] E2E: Playwright Audit Check"
E2E_COUNT=$(find "tests/e2e" -name "*.js" 2>/dev/null | wc -l)
if [ "$E2E_COUNT" -gt 0 ]; then
    ok "$E2E_COUNT E2E-Audit-Scripts in tests/e2e gefunden"
else
    error "KEINE E2E-Tests in tests/e2e gefunden! UX-Verifikation fehlt."
    exit 1
fi

# --- ABSCHLUSS ---

ok "Preflight FAST: Alles grün!"

echo "------------------------------------------------"
echo "🔍 UX-AUDIT REMINDER"
echo "Bitte Claude nun bitten: 'Führe den Visual Auditor für die betroffenen Seiten aus.'"
echo "Nutze dazu die Scripts in: tests/e2e/"
echo "------------------------------------------------"