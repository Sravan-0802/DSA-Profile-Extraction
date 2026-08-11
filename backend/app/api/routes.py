"""HTTP API: config, job creation, status polling, and CSV download."""
from __future__ import annotations

import csv
import io
import json
import re
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from ..config import get_settings
from ..constants import ANALYSIS_TYPES, SHORTLISTING_MODES
from ..core.extraction import is_ocr_available
from ..core import jobs as jobs_module
from ..core.link_utils import normalize_profile_url
from ..core.output import apply_filters, to_csv
from ..schemas import ConfigResponse, JobCreateResponse, JobPayload, JobStatusResponse

router = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# Input parsing
# ---------------------------------------------------------------------------
_EMPTY_MARKERS = {"", "-", "--", "n/a", "na", "none", "null", "nil"}

# Map diverse spreadsheet headers onto canonical row keys.
_HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "user_id": ("user_id", "uid", "userid", "user id", "id"),
    "resume_link": ("resume link", "resume_link", "resume", "resume url", "resume_url"),
    "leetcode": (
        "leetcode",
        "leetcode_profile",
        "leetcode_profile_url",
        "leetcode_profile_url_link",
        "leetcode url",
        "leetcode_url",
        "leetcode link",
        "leetcode_link",
    ),
    "codechef": (
        "codechef",
        "code_chef",
        "codechef_profile",
        "code_chef_profile",
        "codechef_profile_url",
        "code_chef_profile_url",
        "code_chef_profile_url_link",
        "codechef url",
        "codechef_url",
        "codechef link",
        "codechef_link",
    ),
    "codeforces": (
        "codeforces",
        "codeforces_profile",
        "codeforces_profile_url",
        "codeforces_profile_link",
        "codeforces url",
        "codeforces_url",
        "codeforces link",
        "codeforces_link",
        "cf_profile",
        "cf_url",
    ),
    "github": ("github", "github_profile", "github_url", "github url", "github_link", "github link"),
    "hackerrank": (
        "hackerrank",
        "hacker_rank",
        "hackerrank_profile",
        "hackerrank_url",
        "hackerrank url",
        "hackerrank_link",
        "hackerrank link",
    ),
}


def _clean_cell(value: str | None) -> str:
    text = (value or "").strip()
    if text.lower() in _EMPTY_MARKERS:
        return ""
    return text


def _canonical_header(name: str) -> str | None:
    key = re.sub(r"\s+", " ", (name or "").strip().lower())
    key = key.replace("-", "_")
    # Also try space→underscore form so "leetcode profile url link" matches.
    variants = {key, key.replace(" ", "_"), key.replace("_", " ")}
    for canonical, aliases in _HEADER_ALIASES.items():
        alias_set = set(aliases)
        if variants & alias_set:
            return canonical
    # Fuzzy fallback: header contains a platform keyword.
    compact = key.replace(" ", "").replace("_", "")
    for canonical in ("leetcode", "codechef", "codeforces", "github", "hackerrank", "user_id", "resume_link"):
        if canonical.replace("_", "") in compact:
            return canonical
    return None


def _looks_like_header(cells: list[str]) -> bool:
    mapped = [_canonical_header(c) for c in cells if c.strip()]
    known = {m for m in mapped if m}
    return "user_id" in known and bool(known & {"resume_link", "leetcode", "codechef", "codeforces", "github", "hackerrank"})


def _row_dict_from_mapped(raw: dict[str, str]) -> dict[str, str]:
    platforms = ("leetcode", "codechef", "codeforces", "github", "hackerrank")
    row = {
        "user_id": _clean_cell(raw.get("user_id")),
        "resume_link": _clean_cell(raw.get("resume_link")),
        **{p: _clean_cell(raw.get(p)) for p in platforms},
    }
    # Drop non-platform URLs pasted into the wrong column (e.g. tinyurl portfolios).
    for p in platforms:
        if row[p]:
            row[p] = normalize_profile_url(row[p], p)
    return row


def _normalize_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out = []
    for r in rows:
        row = _row_dict_from_mapped(r)
        if any(row.values()):
            out.append(row)
    return out


def parse_pasted(text: str) -> list[dict[str, str]]:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []

    delim = "\t" if "\t" in lines[0] else ","
    first_cells = [c.strip() for c in lines[0].split(delim)]

    if _looks_like_header(first_cells):
        field_map: dict[int, str] = {}
        for idx, cell in enumerate(first_cells):
            canonical = _canonical_header(cell)
            if canonical and idx not in field_map:
                field_map[idx] = canonical
        rows: list[dict[str, str]] = []
        for line in lines[1:]:
            parts = [c.strip() for c in line.split(delim)]
            raw: dict[str, str] = {}
            for idx, key in field_map.items():
                if idx < len(parts):
                    raw[key] = parts[idx]
            rows.append(raw)
        return _normalize_rows(rows)

    # Legacy: UID + resume link (no header). Extra URL columns are ignored here;
    # use a header row for direct platform-profile pastes.
    rows = []
    for line in lines:
        parts = line.split(delim)
        uid = parts[0].strip() if parts else ""
        link = parts[1].strip() if len(parts) > 1 else ""
        rows.append({"user_id": uid, "resume_link": link})
    return _normalize_rows(rows)


def parse_csv(content: bytes) -> list[dict[str, str]]:
    text = content.decode("utf-8-sig", errors="replace")
    # Prefer tab if the payload looks like a TSV paste saved as .csv
    sample = text[:2048]
    dialect_delim = "\t" if sample.count("\t") > sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=dialect_delim)
    rows = []
    for raw in reader:
        mapped: dict[str, str] = {}
        for k, v in raw.items():
            canonical = _canonical_header(k or "")
            if canonical and canonical not in mapped:
                mapped[canonical] = v or ""
        rows.append(mapped)
    return _normalize_rows(rows)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/config", response_model=ConfigResponse)
def get_config() -> ConfigResponse:
    s = get_settings()
    return ConfigResponse(
        has_ai=s.has_ai,
        mistral_key_count=len(s.mistral_keys),
        mistral_model=s.mistral_model,
        has_github=s.has_github,
        github_token_count=len(s.github_tokens),
        ocr_available=is_ocr_available(),
        default_concurrency=s.default_concurrency,
        max_concurrency=s.max_concurrency,
        analysis_types=ANALYSIS_TYPES,
        shortlisting_modes=SHORTLISTING_MODES,
    )


def _serialize(job: jobs_module.JobRecord) -> JobStatusResponse:
    final = job.live_results if job.status == "completed" else []
    return JobStatusResponse(
        id=job.id,
        status=job.status,
        total=job.total,
        completed=job.completed,
        progress=(job.completed / job.total) if job.total else 0.0,
        payload=job.payload,
        warnings=job.warnings,
        errors=job.errors,
        started_at=job.started_at,
        finished_at=job.finished_at,
        live_results=job.live_results,
        results=final,
        file_name=job.file_name,
    )


@router.post("/jobs", response_model=JobCreateResponse, status_code=202)
async def create_job(
    mode: str = Form(...),
    analysis_type: str = Form("All Data"),
    shortlisting_mode: str = Form("Priority Wise (P1 / P2 / P3 Bands)"),
    user_requirements: str = Form(""),
    github_skills: str = Form(""),
    company_name: str = Form(""),
    concurrency: int = Form(8),
    input_method: str = Form("text"),
    pasted_text: str = Form(""),
    csv_file: Optional[UploadFile] = File(None),
) -> JobCreateResponse:
    settings = get_settings()

    if mode == "dsa":
        effective_mode = "dsa"
    elif mode == "github":
        effective_mode = "github"
    elif mode == "shortlisting" and user_requirements.strip():
        effective_mode = "shortlisting"
    else:
        effective_mode = "extraction"

    # Shortlisting, extraction and GitHub analysis all call the AI; DSA is a no-AI run.
    if effective_mode == "shortlisting" and not settings.has_ai:
        raise HTTPException(400, "No Mistral API key configured; AI analysis is unavailable.")
    if effective_mode == "extraction" and not settings.has_ai:
        raise HTTPException(
            400,
            "No Mistral API key configured. Use the 'DSA Profile Extraction' tab for a "
            "no-AI run, or add a key to backend/.env.",
        )
    if effective_mode == "github":
        if not settings.has_ai:
            raise HTTPException(
                400,
                "GitHub Analysis needs a Mistral API key to locate the candidate's "
                "profile. Add one to backend/.env.",
            )
        if not github_skills.strip():
            raise HTTPException(400, "Enter the required tech stack to screen GitHub profiles against.")

    if input_method == "csv" and csv_file is not None:
        rows = parse_csv(await csv_file.read())
    else:
        rows = parse_pasted(pasted_text)

    if not rows:
        raise HTTPException(
            400,
            "No valid rows found. Paste 'UID<TAB>resume_link' lines, or for DSA mode a headered "
            "table with user_id + leetcode/codechef/codeforces profile URL columns.",
        )

    payload = JobPayload(
        mode=effective_mode,
        analysis_type=analysis_type,
        shortlisting_mode=shortlisting_mode,
        user_requirements=user_requirements,
        github_skills=github_skills,
        company_name=company_name,
        concurrency=concurrency,
    )
    job = jobs_module.create_job(payload, rows)
    jobs_module.schedule_job(job.id)
    return JobCreateResponse(job_id=job.id, total_rows=len(rows), message="Job queued")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def job_status(job_id: str) -> JobStatusResponse:
    job = jobs_module.get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return _serialize(job)


@router.get("/jobs/{job_id}/download")
def download_csv(job_id: str, filters: Optional[str] = None):
    job = jobs_module.get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    results = job.live_results
    filter_obj = None
    if filters:
        try:
            filter_obj = json.loads(filters)
        except json.JSONDecodeError:
            filter_obj = None
    csv_text = to_csv(apply_filters(results, filter_obj))
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{job.file_name}"'},
    )
