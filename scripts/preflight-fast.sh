#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source ./scripts/_fmt.sh

info "Preflight FAST startet (schnell, offline-faehig)"

run "[1/5] YAML: docker-compose.yml hat keine Tabs" bash -lc '
  # Tabs in YAML sind fast immer ein Fehler
  if grep -n $'"'"'\t'"'"' docker-compose.yml >/dev/null 2>&1; then
    echo "Tabs gefunden:"
    grep -n $'"'"'\t'"'"' docker-compose.yml || true
    exit 1
  fi
'

run "[2/5] YAML: docker compose config validiert" docker compose config >/dev/null

run "[3/5] Docs: kein Copy-Paste Artefakt \\_local" bash -lc '
  if grep -R --line-number "\\\\_local" README.md .gitignore docker-compose.yml >/dev/null 2>&1; then
    echo "Gefunden (bitte _local ohne Backslash verwenden):"
    grep -R --line-number "\\\\_local" README.md .gitignore docker-compose.yml || true
    exit 1
  fi
'

run "[4/5] Code: keine Markdown Artefakte (**future**, **file**) in Python" bash -lc '
  if grep -R --line-number -E "\\*\\*future\\*\\*|\\*\\*file\\*\\*" app --include="*.py" >/dev/null 2>&1; then
    echo "Gefunden (das ist kaputter Copy-Paste aus Markdown):"
    grep -R --line-number -E "\\*\\*future\\*\\*|\\*\\*file\\*\\*" app --include="*.py" || true
    exit 1
  fi
'

step "[5/5] Python: lokaler Syntax-Compile (ohne Docker)"
PYBIN=""
if command -v python3 >/dev/null 2>&1; then PYBIN="python3"; fi
if command -v python  >/dev/null 2>&1; then PYBIN="python";  fi
if [ -z "$PYBIN" ]; then
  fail "python/python3 nicht gefunden. Installiere Python 3 oder nutze preflight-deep.sh."
  exit 1
fi
"$PYBIN" -m compileall -q app
ok "[5/5] Python: lokaler Syntax-Compile (ohne Docker)"

ok "Preflight FAST: alles gruen"
