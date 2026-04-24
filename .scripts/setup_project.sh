#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v python3.11 >/dev/null 2>&1; then
  echo "python3.11 is required but was not found in PATH."
  echo "Install Python 3.11 and re-run setup."
  exit 1
fi

if [[ ! -d .venv ]]; then
  python3.11 -m venv .venv
elif ! .venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)'; then
  echo "Existing .venv is not Python 3.11. Remove it and run setup again: rm -rf .venv"
  exit 1
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

echo "Setup complete."
echo "Run: source .venv/bin/activate && macbook-power-widget"
