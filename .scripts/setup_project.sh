#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Pick a Python interpreter: prefer existing .venv, else the newest available
# python3.x on PATH (>=3.9), matching the pyproject `requires-python` range.
MIN_MAJOR=3
MIN_MINOR=9

version_ok() {
    "$1" -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (${MIN_MAJOR}, ${MIN_MINOR}) else 1)" >/dev/null 2>&1
}

PYTHON=""
if [[ -x .venv/bin/python ]] && version_ok .venv/bin/python; then
    PYTHON=".venv/bin/python"
else
    for candidate in python3.13 python3.12 python3.11 python3.10 python3.9 python3; do
        if command -v "${candidate}" >/dev/null 2>&1 && version_ok "${candidate}"; then
            PYTHON="${candidate}"
            break
        fi
    done
fi

if [[ -z "${PYTHON}" ]]; then
    echo "Python >= ${MIN_MAJOR}.${MIN_MINOR} is required but was not found in PATH."
    exit 1
fi

echo "Using Python: $(${PYTHON} -c 'import sys; print(sys.executable, sys.version.split()[0])')"

if [[ ! -d .venv ]]; then
    "${PYTHON}" -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

echo "Setup complete."
echo "Run: source .venv/bin/activate && macbook-power-widget"
