#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Auto-activate the project venv when invoked outside an already-activated shell
if [[ -z "${VIRTUAL_ENV:-}" ]] && [[ -f .venv/bin/activate ]]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

python -m pip install --upgrade pip
python -m pip install build twine

rm -rf dist/ build/
python -m build
python -m twine check dist/*

echo "Build artifacts created in dist/"
