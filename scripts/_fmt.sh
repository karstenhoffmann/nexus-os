#!/usr/bin/env bash
set -euo pipefail

_is_tty() { [ -t 1 ]; }

# Colors (only if TTY)
if _is_tty; then
  C_RESET=$'\033[0m'
  C_RED=$'\033[0;31m'
  C_GREEN=$'\033[0;32m'
  C_YELLOW=$'\033[0;33m'
  C_BLUE=$'\033[0;34m'
  C_DIM=$'\033[0;2m'
else
  C_RESET=""
  C_RED=""
  C_GREEN=""
  C_YELLOW=""
  C_BLUE=""
  C_DIM=""
fi

info()  { echo "${C_BLUE}ℹ️  $*${C_RESET}"; }
step()  { echo "${C_DIM}🔎 $*${C_RESET}"; }
ok()    { echo "${C_GREEN}✅ $*${C_RESET}"; }
warn()  { echo "${C_YELLOW}⚠️  $*${C_RESET}"; }
fail()  { echo "${C_RED}❌ $*${C_RESET}" 1>&2; }

# Run a command with a readable status line
run() {
  local label="$1"; shift
  step "$label"
  "$@"
  ok "$label"
}

# Better error message on any failure
on_err() {
  local code=$?
  fail "Fehler (exit $code) in $0 (Zeile $1). Letzter Befehl: $2"
  exit "$code"
}

trap 'on_err $LINENO "$BASH_COMMAND"' ERR
