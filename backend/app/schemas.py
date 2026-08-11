"""Pydantic models for API requests/responses."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class JobPayload(BaseModel):
    mode: str   # extraction | shortlisting | dsa | github
    analysis_type: str = "All Data"
    shortlisting_mode: str = "Priority Wise (P1 / P2 / P3 Bands)"
    user_requirements: str = ""
    github_skills: str = ""         # github mode: required tech stack to screen for
    company_name: str = ""
    concurrency: int = 8


class JobCreateResponse(BaseModel):
    job_id: str
    total_rows: int
    message: str


class JobStatusResponse(BaseModel):
    id: str
    status: str                     # queued | running | completed | failed
    total: int
    completed: int
    progress: float                 # 0..1
    payload: JobPayload
    warnings: list[str] = []
    errors: list[str] = []
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    live_results: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    file_name: str = ""


class ConfigResponse(BaseModel):
    has_ai: bool
    mistral_key_count: int
    mistral_model: str
    has_github: bool
    github_token_count: int
    ocr_available: bool
    default_concurrency: int
    max_concurrency: int
    analysis_types: list[str]
    shortlisting_modes: list[str]
