"""Internal-project list loading and AI project classification."""
from __future__ import annotations

import logging
from functools import lru_cache

from ..config import INTERNAL_PROJECT_LIST_PATH
from .utils import safe_str

logger = logging.getLogger(__name__)


@lru_cache
def get_internal_projects_string() -> str:
    """Load internal project names as a comma-separated string for prompts."""
    try:
        with open(INTERNAL_PROJECT_LIST_PATH, "r", encoding="utf-8") as fh:
            projects = [line.strip() for line in fh if line.strip()]
        return ", ".join(projects)
    except FileNotFoundError:
        logger.warning("Internal project list not found at %s", INTERNAL_PROJECT_LIST_PATH)
        return ""


def classify_and_format_projects(projects) -> dict[str, str]:
    """Split AI-extracted projects into internal/external title & techstack blocks."""
    internal_titles, internal_techs = [], []
    external_titles, external_techs = [], []

    if not isinstance(projects, list):
        projects = []

    for p in projects:
        if not isinstance(p, dict):
            continue
        title = safe_str(p.get("title", "")).strip()
        if not title:
            continue
        tech = p.get("techStack", [])
        tech_str = ", ".join(safe_str(t) for t in tech) if isinstance(tech, list) else safe_str(tech).strip()
        classification = safe_str(p.get("classification", "External")).lower()
        if classification == "internal":
            internal_titles.append(title)
            if tech_str:
                internal_techs.append(tech_str)
        else:
            external_titles.append(title)
            if tech_str:
                external_techs.append(tech_str)

    return {
        "Internal Project Title": "\n".join(internal_titles),
        "Internal Projects Techstacks": "\n".join(internal_techs),
        "External Project Title": "\n".join(external_titles),
        "External Projects Techstacks": "\n".join(external_techs),
    }


def project_instruction_block(internal_projects_string: str) -> str:
    if internal_projects_string:
        return (
            '\n"projects": Analyze the resume for projects. For each project, extract its '
            'title and techStack. CRITICALLY, add a "classification" field. Classify a '
            'project as "Internal" if its title/description matches any project from the '
            "OFFICIAL INTERNAL PROJECTS LIST below; otherwise classify it as \"External\". "
            "Be flexible in matching (e.g. 'Jobby App' matches 'Jobby-app').\n"
            f"OFFICIAL INTERNAL PROJECTS LIST: {internal_projects_string}\n"
            'Example: {{ "title": "Jobby App", "techStack": ["React", "JS"], "classification": "Internal" }}\n'
        )
    return (
        '\n"projects": [ {{ "title": "string", "techStack": ["list of tech keywords"], '
        '"classification": "External" }} ]\n'
    )
