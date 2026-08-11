#!/usr/bin/env bash
# Production run step — deps already installed by build.sh.
# Just starts the FastAPI server.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

PORT="${PORT:-5000}"
echo "==> Starting server on 0.0.0.0:${PORT}"
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
