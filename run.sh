#!/usr/bin/env bash
# Fejlesztői indítás: ./run.sh  (http://localhost:8080)
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  ./.venv/bin/pip install -q --upgrade pip
  ./.venv/bin/pip install -q -r requirements.txt
fi
exec ./.venv/bin/python -m panel
