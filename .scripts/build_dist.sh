#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python -m pip install --upgrade pip
python -m pip install build twine

rm -rf dist/ build/
python -m build
python -m twine check dist/*

echo "Build artifacts created in dist/"
