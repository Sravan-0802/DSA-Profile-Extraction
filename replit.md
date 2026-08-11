# Resume Intelligence Tool

A single-port React + FastAPI application that combines resume parsing, candidate shortlisting, and coding-platform stats into one tool.

## Stack

- **Frontend:** React 18 + TypeScript + Vite (built to `frontend/dist/`)
- **Backend:** FastAPI + Uvicorn (Python 3.12), served on port 5000
- **AI:** Mistral API (round-robin multi-key support)
- **PDF:** pdfplumber + PyMuPDF; optional Tesseract OCR

## Running locally (development)

```bash
bash scripts/start.sh
```

This installs all deps, builds the frontend, and starts FastAPI on port 5000. The workflow `Start application` is configured to run this automatically.

## Running in production (deployment)

Two-step process configured in `.replit` `[deployment]`:

| Step | Script | Purpose |
|------|--------|---------|
| Build | `scripts/build.sh` | npm install + vite build + pip install (needs network) |
| Run | `scripts/prod_start.sh` | Starts uvicorn only (no network needed) |

> **Important:** `pip install` must happen in the build step. The deployment runtime container blocks outbound network access, so installing packages at startup fails.

## Secrets

| Secret | Required | Purpose |
|--------|----------|---------|
| `MISTRAL_API_KEY` | For AI modes | Resume parsing, scoring, shortlisting |
| `GITHUB_TOKEN` | Recommended | GitHub analysis (raises rate limit 60→5000 req/hr) |

Multiple keys supported: `MISTRAL_API_KEY_1`, `MISTRAL_API_KEY_2`, etc. (round-robin).

## Environment variables (non-secret)

Set in Replit shared environment:

| Variable | Default | Purpose |
|----------|---------|---------|
| `MISTRAL_MODEL` | `mistral-large-latest` | Mistral model |
| `DEFAULT_CONCURRENCY` | `8` | Parallel resume workers |
| `MAX_CONCURRENCY` | `20` | Hard cap |
| `ENABLE_OCR` | `false` | Tesseract OCR (binary not installed by default) |
| `CORS_ORIGINS` | `*` | Allowed origins (single-port deploy — `*` is safe) |

## User preferences

- Keep the existing project structure (backend/ + frontend/ layout).
