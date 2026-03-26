#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
PACKAGE_NAME="bookkeeping-tool"
BUILD_VENV_DIR="$ROOT_DIR/.build-venv"

cd "$ROOT_DIR"

PYTHON_BIN="/opt/homebrew/opt/python@3.11/bin/python3.11"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Missing required Python: $PYTHON_BIN" >&2
  exit 1
fi

rm -rf "$BUILD_VENV_DIR"
"$PYTHON_BIN" -m venv "$BUILD_VENV_DIR"
"$BUILD_VENV_DIR/bin/pip" install --upgrade pip build pyinstaller

VERSION="$($PYTHON_BIN - <<'PY'
import pathlib
import re
text = pathlib.Path('pyproject.toml').read_text()
match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
if not match:
    raise SystemExit('Unable to find version in pyproject.toml')
print(match.group(1))
PY
)"

PLATFORM="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"
ARTIFACT_BASENAME="$PACKAGE_NAME-$PLATFORM-$ARCH-v$VERSION"
BUNDLE_DIR="$DIST_DIR/$ARTIFACT_BASENAME"
PYINSTALLER_DIST_DIR="$ROOT_DIR/pyinstaller-dist"
PYINSTALLER_BUILD_DIR="$ROOT_DIR/pyinstaller-build"
SPEC_FILE="$ROOT_DIR/bookkeeping.spec"

rm -rf build dist *.egg-info src/bookkeeping_tool.egg-info "$PYINSTALLER_DIST_DIR" "$PYINSTALLER_BUILD_DIR" "$SPEC_FILE"
mkdir -p "$DIST_DIR" "$BUNDLE_DIR"

if [ -d "frontend" ]; then
  cd frontend
  npm install
  npm run build
  cd "$ROOT_DIR"
fi

"$BUILD_VENV_DIR/bin/python" -m build
"$BUILD_VENV_DIR/bin/pip" install "$DIST_DIR"/*.whl

"$BUILD_VENV_DIR/bin/pyinstaller" \
  --clean \
  --noconfirm \
  --onefile \
  --name bookkeeping \
  --distpath "$PYINSTALLER_DIST_DIR" \
  --workpath "$PYINSTALLER_BUILD_DIR" \
  --specpath "$ROOT_DIR" \
  --copy-metadata bookkeeping-tool \
  --collect-all bookkeeping_tool \
  --hidden-import uvicorn.logging \
  --hidden-import uvicorn.loops \
  --hidden-import uvicorn.loops.auto \
  --hidden-import uvicorn.protocols \
  --hidden-import uvicorn.protocols.http \
  --hidden-import uvicorn.protocols.websockets \
  --hidden-import uvicorn.lifespan \
  --hidden-import uvicorn.lifespan.on \
  --hidden-import uvicorn.lifespan.off \
  --hidden-import pandas \
  --hidden-import openpyxl \
  --hidden-import typer \
  --hidden-import rich \
  --hidden-import fastapi \
  --hidden-import pydantic \
  --hidden-import starlette \
  "$BUILD_VENV_DIR/bin/bookkeeping"

cp "$PYINSTALLER_DIST_DIR/bookkeeping" "$BUNDLE_DIR/bookkeeping"
chmod 0755 "$BUNDLE_DIR/bookkeeping"

tar -C "$DIST_DIR" -czf "$DIST_DIR/$ARTIFACT_BASENAME.tar.gz" "$ARTIFACT_BASENAME"
