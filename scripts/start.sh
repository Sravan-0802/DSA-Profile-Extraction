#!/usr/bin/env bash
# Single-port production start (Replit / Docker / VM).
# Builds the React UI, then serves API + UI from FastAPI on $PORT (default 5000).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Installing frontend deps"
(cd frontend && npm install)

echo "==> Building frontend"
(cd frontend && npm run build)

echo "==> Installing backend deps"
python3 -m pip install -r backend/requirements.txt

PORT="${PORT:-5000}"
echo "==> Starting server on 0.0.0.0:${PORT}"
cd backend
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
