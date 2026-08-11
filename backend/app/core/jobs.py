"""In-memory job store with an asyncio worker pool and Mistral key rotation."""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from ..config import get_settings
from ..schemas import JobPayload
from .processor import process_one

logger = logging.getLogger(__name__)


@dataclass
class JobRecord:
    id: str
    payload: JobPayload
    rows: list[dict[str, str]]
    status: str = "queued"
    completed: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    # slot-indexed so live results preserve input order as they fill in
    slots: list[Optional[dict[str, Any]]] = field(default_factory=list)
    file_name: str = ""

    @property
    def total(self) -> int:
        return len(self.rows)

    @property
    def live_results(self) -> list[dict[str, Any]]:
        return [s for s in self.slots if s is not None]


_JOBS: dict[str, JobRecord] = {}
# Hold strong references to running background tasks so they are not GC'd.
_TASKS: set[asyncio.Task] = set()


def schedule_job(job_id: str) -> None:
    """Start a job's background processing task, retaining a strong reference."""
    task = asyncio.create_task(run_job(job_id))
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _file_name(payload: JobPayload) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if payload.mode == "shortlisting":
        tag = "shortlisting"
    elif payload.mode == "dsa":
        tag = "dsa_profiles"
    elif payload.mode == "github":
        tag = "github_analysis"
    else:
        tag = payload.analysis_type.replace(" ", "_")
    return f"resume_analysis_{tag}_{stamp}.csv"


def create_job(payload: JobPayload, rows: list[dict[str, str]]) -> JobRecord:
    job = JobRecord(
        id=str(uuid.uuid4()),
        payload=payload,
        rows=rows,
        slots=[None] * len(rows),
        file_name=_file_name(payload),
    )
    _JOBS[job.id] = job
    return job


def get_job(job_id: str) -> Optional[JobRecord]:
    return _JOBS.get(job_id)


async def run_job(job_id: str) -> None:
    """Background task: process all rows concurrently with a semaphore."""
    job = _JOBS.get(job_id)
    if job is None:
        return

    settings = get_settings()
    keys = settings.mistral_keys or [""]
    job.status = "running"
    job.started_at = _now()

    concurrency = max(1, min(job.payload.concurrency, settings.max_concurrency))
    sem = asyncio.Semaphore(concurrency)

    async def worker(index: int, row: dict[str, str]) -> None:
        async with sem:
            api_key = keys[index % len(keys)]
            profiles = {
                "leetcode": row.get("leetcode", ""),
                "codechef": row.get("codechef", ""),
                "codeforces": row.get("codeforces", ""),
                "github": row.get("github", ""),
                "hackerrank": row.get("hackerrank", ""),
            }
            try:
                result = await asyncio.to_thread(
                    process_one,
                    row.get("user_id", ""),
                    row.get("resume_link", ""),
                    mode=job.payload.mode,
                    analysis_type=job.payload.analysis_type,
                    shortlisting_mode=job.payload.shortlisting_mode,
                    user_requirements=job.payload.user_requirements,
                    github_skills=job.payload.github_skills,
                    company_name=job.payload.company_name,
                    api_key=api_key,
                    profiles=profiles,
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Worker crashed for row %d", index)
                result = {
                    "User ID": row.get("user_id", ""),
                    "Resume Link": row.get("resume_link", ""),
                    "Error": f"Error: {exc}",
                }
                job.errors.append(f"Row {index + 1}: {exc}")
            job.slots[index] = result
            job.completed += 1

    try:
        await asyncio.gather(*(worker(i, row) for i, row in enumerate(job.rows)))
        job.status = "completed"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Job %s failed", job_id)
        job.status = "failed"
        job.errors.append(str(exc))
    finally:
        job.finished_at = _now()
