#!/usr/bin/env bash
# Deployment build step — runs with network access.
# Installs all dependencies and compiles the frontend.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Installing frontend deps"
(cd frontend && npm install)

echo "==> Building frontend"
(cd frontend && npm run build)

echo "==> Installing backend deps"
python3 -m pip install -r backend/requirements.txt

echo "==> Build complete"
