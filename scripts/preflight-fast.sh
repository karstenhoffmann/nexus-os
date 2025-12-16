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

echo "[1/5] YAML: docker-compose.yml has no tabs"
if grep -nP '\t' docker-compose.yml >/dev/null 2>&1; then
  print_status error "Tabs found in docker-compose.yml (YAML needs spaces)."
  exit 1
else
  print_status ok "No tabs found in docker-compose.yml."
fi

echo "[2/5] YAML: docker compose config validates"
if docker compose config >/dev/null 2>&1; then
  print_status ok "docker-compose.yml is valid."
else
  print_status error "docker-compose.yml is invalid."
  exit 1
fi

echo "[3/5] Docs: no copy-paste artefacts like \\_local"
if grep -R --line-number '\\_local' README.md .gitignore docker-compose.yml >/dev/null 2>&1; then
  print_status error "Found '\\_local' escaping. Use '_local' literally."
  exit 1
else
  print_status ok "No '\\_local' escaping found."
fi

echo "[4/5] Code: no markdown artefacts (**future**, **file**) in Python"
if grep -R --line-number -E '\*\*future\*\*|\*\*file\*\*' app --include='*.py' >/dev/null 2>&1; then
  print_status error "Found markdown artefacts in Python files."
  exit 1
else
  print_status ok "No markdown artefacts in Python files."
fi

echo "[5/5] Python: local syntax compile (no Docker)"
PYBIN=""
if command -v python3 >/dev/null 2>&1; then PYBIN="python3"; fi
if command -v python >/dev/null 2>&1; then PYBIN="python"; fi
if [ -z "$PYBIN" ]; then
  print_status error "python/python3 not found on host. Install Python 3 or rely on preflight-deep.sh."
  exit 1
fi
"$PYBIN" -m compileall -q app
print_status ok "Python syntax check passed."

echo "✅ preflight-fast passed"
