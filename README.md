# Resume Intelligence Tool

A single React + FastAPI application that merges three previously-scattered tools:

1. **DSA Extractor** — pulls coding-platform profiles (GitHub / LeetCode / Codeforces /
   CodeChef / HackerRank) from a resume and fetches **solved-problem counts**.
2. **Resume-analyzer** — Mistral-AI resume parsing, skill scoring, and P1/P2/P3
   candidate shortlisting.
3. **ResumePBS** — the job-queue / live-progress / filter-and-download UX pattern,
   reimplemented on FastAPI.

> Excluded by design: Google Sheets write-back, BigQuery, and the Electron desktop app.

## Features

- **Data extraction** modes: All Data · Personal Details · Skills & Projects · Internal Projects Matching
- **Shortlisting**: score candidates against a job description → Probability or Priority (P1/P2/P3) bands
- **Coding-platform stats** (opt-in toggle): profile links + LeetCode/Codeforces/CodeChef solved counts, addable to any run
- Google Docs / Google Drive / direct PDF download, with OCR fallback for scanned files
- Concurrent processing with multi-key Mistral round-robin, live progress, interactive filters, CSV export

## Project layout

```
Resume-Tool/
├── backend/    FastAPI app (app/), requirements.txt, .env.example
└── frontend/   React + Vite + TypeScript
```

## Prerequisites

- Python 3.11+ (tested on 3.14)
- Node 18+ (tested on 24)
- **Mistral API key** for any AI mode. Get one at https://console.mistral.ai
  (a coding-stats-only run needs no key.)
- *(Optional)* Tesseract OCR — only for scanned/image resumes.
  Windows: https://github.com/UB-Mannheim/tesseract/wiki

## Setup & run

### 1. Backend

```bash
cd backend
py -m venv venv
venv\Scripts\activate            # Windows  (source venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
copy .env.example .env           # then edit .env and paste your MISTRAL_API_KEY
uvicorn app.main:app --port 8000 --reload
```

Backend runs at http://localhost:8000 (interactive docs at `/docs`).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server proxies `/api/*` to the backend, so no
CORS setup is needed during development.

## Configuration (`backend/.env`)

| Variable | Purpose |
|---|---|
| `MISTRAL_API_KEY` | Single key. Or use `MISTRAL_API_KEY_1..12` for round-robin throughput. |
| `MISTRAL_MODEL` | Default `mistral-large-latest`. |
| `DEFAULT_CONCURRENCY` / `MAX_CONCURRENCY` | Parallel resume workers. |
| `ENABLE_OCR` / `TESSERACT_CMD` | OCR fallback toggle + optional binary path. |
| `CORS_ORIGINS` | Allowed origins (needed only if you don't use the Vite proxy). |

## API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/config` | Capabilities (keys, OCR, modes). |
| POST | `/api/jobs` | Create a job (multipart form). Returns `{ job_id }`. |
| GET | `/api/jobs/{id}` | Poll status + live/final results. |
| GET | `/api/jobs/{id}/download?filters=…` | Download filtered results as CSV. |

## Input format

Paste rows as `UID<TAB>resume_link` (tab- or comma-separated), one per line, or
upload a CSV with columns `user_id, Resume link`.

## Notes

- Jobs are held **in memory** — results clear when the backend restarts. (Ask if you
  want SQLite persistence added.)
- Per-row failures are captured in an `Error` column; the batch always completes.
- The internal-project classifier reads `backend/app/resources/INTERNAL_PROJECT_LIST.txt`
  — edit that file to change the official project list.
