"""Process a single resume end-to-end: fetch -> analyze -> (optional) DSA stats."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from .analyzers import analyze_comprehensive, analyze_shortlisting
from .dsa_stats import collect_dsa_stats
from .extraction import fetch_resume
from .github_analysis import analyze_github
from .link_utils import categorize_links, normalize_profile_url

logger = logging.getLogger(__name__)


def _profiles_from_row(profiles: Optional[dict[str, str]]) -> dict[str, str]:
    """Keep only real platform URLs; drop '-', empty cells, and off-platform links."""
    out = {
        "github": "",
        "leetcode": "",
        "codeforces": "",
        "codechef": "",
        "hackerrank": "",
    }
    if not profiles:
        return out
    for platform in out:
        raw = (profiles.get(platform) or "").strip()
        if not raw:
            continue
        cleaned = normalize_profile_url(raw, platform)
        if cleaned:
            out[platform] = cleaned
    return out


def process_one(
    user_id: str,
    resume_link: str,
    *,
    mode: str,                 # "shortlisting" | "extraction" | "dsa" | "github"
    analysis_type: str,
    shortlisting_mode: str,
    user_requirements: str,
    github_skills: str,
    company_name: str,
    api_key: str,
    profiles: Optional[dict[str, str]] = None,
) -> dict:
    """Synchronous worker (run in a thread). Always returns a result dict."""
    result: dict = {"User ID": user_id, "Resume Link": resume_link}
    if company_name:
        result["Company Name"] = company_name

    try:
        direct = _profiles_from_row(profiles)
        has_direct = any(direct.values())

        # DSA with pasted platform URLs — skip resume download entirely.
        if mode == "dsa" and has_direct:
            result.update(collect_dsa_stats(direct))
        elif mode == "dsa" and not resume_link.strip():
            # Row has only a user_id (or blank profiles like "-") — still emit zeroed columns.
            result.update(collect_dsa_stats(direct))
        else:
            text, links = fetch_resume(resume_link)
            if not text or not text.strip():
                raise ValueError("Could not extract any text from the file.")

            lower_text = text.lower()
            if mode == "shortlisting":
                ai_result = analyze_shortlisting(
                    lower_text,
                    user_requirements,
                    shortlisting_mode,
                    api_key,
                )
                result.update(ai_result)
            elif mode == "extraction":
                ai_result = analyze_comprehensive(
                    lower_text,
                    links,
                    analysis_type,
                    api_key,
                )
                result.update(ai_result)

            elif mode == "dsa":
                # Fall back: scrape profiles out of the resume, then fetch counts.
                found = categorize_links(text, links)
                result.update(collect_dsa_stats(found))

            elif mode == "github":
                result.update(analyze_github(text, links, github_skills, api_key))

            else:
                raise ValueError(f"Unknown mode: {mode}")

    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed processing %s (%s): %s", user_id, resume_link, exc)
        result["Error"] = f"Error: {exc}"

    result["Analysis Datetime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return result
