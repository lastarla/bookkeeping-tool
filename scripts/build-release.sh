#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$ROOT_DIR"

PYTHON_BIN=""
for candidate in python python3 /opt/homebrew/opt/python@3.11/bin/python3.11 /opt/homebrew/bin/python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -m build --version >/dev/null 2>&1; then
    PYTHON_BIN="$candidate"
    break
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  echo "No Python interpreter with 'python -m build' available" >&2
  exit 1
fi

rm -rf build dist *.egg-info src/bookkeeping_tool.egg-info

if [ -d "frontend" ]; then
  cd frontend
  npm install
  npm run build
  cd "$ROOT_DIR"
fi

"$PYTHON_BIN" -m build
