#!/usr/bin/env bash
# build.sh — Sync canonical skills/ to runtime-specific discovery locations.
#
# This is a thin shim over tools/build_skills.py for Unix users.
# The Python script is the canonical build implementation; it works on
# Windows, macOS, and Linux with zero dependencies beyond stdlib.
#
# Direct invocation also works:
#   python tools/build_skills.py
#
# Run from any location — the script resolves paths relative to its own location.

set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
  echo "Error: python or python3 is required but not installed." >&2
  exit 1
fi

# Prefer python3 if available (Linux/macOS), fall back to python (Windows).
PY=$(command -v python3 || command -v python)
exec "$PY" tools/build_skills.py
