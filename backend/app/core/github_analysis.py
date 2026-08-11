"""GitHub technical screening.

Given a resume's text + links and a required tech stack, this module:
  1. Uses the AI to locate the candidate's GitHub profile/username.
  2. Scans their public repos and scores each required technology (0/100)
     based on language share, dependency manifests, topics and description.
  3. Verifies ownership via commit authorship.

Ported from the Streamlit analyzer's GitHub screening module and adapted to
the FastAPI backend (settings-based token rotation, shared AI/JSON helpers).
"""
from __future__ import annotations

import base64
import logging
import re
import threading

import requests

from ..config import get_settings
from .ai import analyze_text_with_mistral
from .utils import relaxed_json_loads, safe_str

logger = logging.getLogger(__name__)

MIN_LANGUAGE_SHARE = 0.25
LANGUAGE_TECH_ALIASES = {
    "javascript": {"javascript"},
    "typescript": {"typescript"},
    "python": {"python"},
    "java": {"java"},
    "php": {"php"},
    "go": {"go"},
    "rust": {"rust"},
    "c#": {"c#", "csharp"},
    ".net": {"c#", "csharp"},
}
_MANIFEST_FILES = (
    "package.json", "requirements.txt", "pyproject.toml", "pom.xml",
    "go.mod", "Cargo.toml", "Web.config",
)

# Round-robin index over the configured GitHub tokens (thread-safe: repos are
# analyzed from a thread pool).
_token_lock = threading.Lock()
_token_idx = 0


def _next_token() -> str:
    tokens = get_settings().github_tokens
    if not tokens:
        return ""
    global _token_idx
    with _token_lock:
        token = tokens[_token_idx % len(tokens)]
        _token_idx += 1
    return token


def _headers(token: str) -> dict:
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _normalize_token(value) -> str:
    return safe_str(value).strip().lower().replace(" ", "")


# ---------------------------------------------------------------------------
# Step 1 — find the candidate's GitHub profile via AI
# ---------------------------------------------------------------------------
def extract_github_info_via_ai(resume_text: str, links: list[str], api_key: str) -> dict:
    prompt = f"""
    Analyze the following resume content and links to find the candidate's GitHub profile.
    Candidates might provide a username, a full URL, or a link hidden in a portfolio site.
    Ignore links ending in '.io' unless they are explicitly GitHub Pages (e.g., username.github.io).

    Resume Text: {resume_text}
    Detected Links: {links}

    Return ONLY a JSON object:
    {{
      "github_found": boolean,
      "github_url": "string or null",
      "github_username": "string or null",
      "reasoning": "string"
    }}
    """
    response = analyze_text_with_mistral(prompt, api_key)
    try:
        data = relaxed_json_loads(response)
        return data if isinstance(data, dict) else {"github_found": False}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not parse GitHub info from AI response: %s", exc)
        return {"github_found": False, "github_url": None, "github_username": None}


# ---------------------------------------------------------------------------
# Step 2 — score the candidate's repositories against required tech
# ---------------------------------------------------------------------------
def analyze_github_repositories(username: str, required_tech: str, token: str) -> dict:
    if not username:
        return {"found": False, "error": "No username"}

    tech_list = [t.strip().lower() for t in re.split(r"[,\s/]+", required_tech) if t.strip()]
    if not tech_list:
        return {"found": False, "error": "No tech stack provided"}

    tech_results = {tech: {"score": 0, "projects": []} for tech in tech_list}
    headers = _headers(token)

    try:
        total_public_repos = 0
        try:
            user_resp = requests.get(
                f"https://api.github.com/users/{username}", headers=headers, timeout=10
            )
            if user_resp.status_code == 200:
                total_public_repos = int(user_resp.json().get("public_repos", 0) or 0)
        except Exception:  # noqa: BLE001
            total_public_repos = 0

        repo_resp = requests.get(
            f"https://api.github.com/users/{username}/repos?per_page=100&sort=updated",
            headers=headers,
            timeout=15,
        )
        if repo_resp.status_code != 200:
            return {
                "found": False,
                "error": f"GitHub API Error: {repo_resp.status_code}",
                "total_public_repos": total_public_repos,
            }

        repos = repo_resp.json()
        if not isinstance(repos, list):
            return {"found": False, "error": "Unexpected repos response", "total_public_repos": total_public_repos}
        if not total_public_repos:
            total_public_repos = len(repos)

        for repo in repos:
            if all(data["score"] == 100 for data in tech_results.values()):
                break

            repo_name = repo.get("name", "")
            owner = (repo.get("owner") or {}).get("login")
            description = (repo.get("description") or "").lower()
            topics = [t.lower() for t in repo.get("topics", [])]
            primary_language = safe_str(repo.get("language", "Unknown")).strip()
            primary_language_norm = _normalize_token(primary_language)

            lang_resp = requests.get(
                f"https://api.github.com/repos/{owner}/{repo_name}/languages",
                headers=headers,
                timeout=5,
            )
            lang_bytes = {}
            if lang_resp.status_code == 200 and isinstance(lang_resp.json(), dict):
                lang_bytes = {
                    _normalize_token(k): int(v or 0)
                    for k, v in lang_resp.json().items()
                    if safe_str(k).strip()
                }
            repo_langs = list(lang_bytes.keys())
            total_lang_bytes = sum(lang_bytes.values())

            frameworks_detected: list[str] = []
            if any(l in ("javascript", "typescript", "python", "java", "c#", "rust", "go") for l in repo_langs):
                for file_name in _MANIFEST_FILES:
                    f_resp = requests.get(
                        f"https://api.github.com/repos/{owner}/{repo_name}/contents/{file_name}",
                        headers=headers,
                        timeout=5,
                    )
                    if f_resp.status_code == 200:
                        try:
                            content = base64.b64decode(
                                f_resp.json().get("content", "") + "==="
                            ).decode("utf-8").lower()
                            for tech in tech_list:
                                if tech_results[tech]["score"] == 100:
                                    continue
                                if tech in content:
                                    frameworks_detected.append(tech)
                        except Exception:  # noqa: BLE001
                            pass

            search_blob = (
                f"{repo_name} {description} {' '.join(topics)} "
                f"{' '.join(repo_langs)} {' '.join(frameworks_detected)}"
            ).lower()

            for tech in tech_list:
                if tech_results[tech]["score"] == 100:
                    continue

                pattern = r"(?i)\.net\b" if tech == ".net" else r"\b" + re.escape(tech) + r"\b"
                is_match = False
                match_reason = "metadata match"

                if tech in LANGUAGE_TECH_ALIASES:
                    aliases = LANGUAGE_TECH_ALIASES[tech]
                    primary_match = primary_language_norm in aliases
                    highest_share = 0.0
                    for alias in aliases:
                        bytes_for_lang = lang_bytes.get(alias, 0)
                        if total_lang_bytes > 0 and bytes_for_lang > 0:
                            share = bytes_for_lang / total_lang_bytes
                            highest_share = max(highest_share, share)
                    if primary_match or highest_share >= MIN_LANGUAGE_SHARE:
                        is_match = True
                        match_reason = (
                            f"primary language: {primary_language or 'Unknown'}"
                            if primary_match
                            else f"language share: {highest_share:.0%}"
                        )
                else:
                    if re.search(pattern, search_blob):
                        is_match = True
                        if tech in frameworks_detected:
                            match_reason = "dependency file match"
                        elif tech in topics:
                            match_reason = "topic match"
                        elif re.search(pattern, description):
                            match_reason = "description match"

                if is_match:
                    v_resp = requests.get(
                        f"https://api.github.com/repos/{owner}/{repo_name}/commits"
                        f"?author={username}&per_page=1",
                        headers=headers,
                        timeout=5,
                    )
                    is_verified = (
                        v_resp.status_code == 200 and len(v_resp.json()) > 0
                    ) or (owner and owner.lower() == username.lower())

                    if is_verified:
                        tech_results[tech]["score"] = 100
                        proj_entry = f"{repo_name} ({primary_language or 'Unknown'}) - {match_reason}"
                        if proj_entry not in tech_results[tech]["projects"]:
                            tech_results[tech]["projects"].append(proj_entry)

        all_scores = [data["score"] for data in tech_results.values()]
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

        return {
            "found": True,
            "tech_details": tech_results,
            "github_average_probability": int(avg_score),
            "match_count": sum(1 for d in tech_results.values() if d["score"] > 0),
            "commits_verified": any(d["score"] > 0 for d in tech_results.values()),
            "total_public_repos": total_public_repos,
        }
    except Exception as exc:  # noqa: BLE001
        return {"found": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Orchestrator — used by the processor for mode == "github"
# ---------------------------------------------------------------------------
def analyze_github(resume_text: str, links: list[str], github_skills: str, api_key: str) -> dict:
    """Return the GitHub-analysis output columns for one candidate."""
    result: dict = {
        "GitHub Screening Outcome": "Error Processing",
        "Profile Used": "None",
        "Ownership": "N/A",
        "GitHub Repo Count": 0,
    }
    input_techs = [t.strip().upper() for t in re.split(r"[,\s/]+", github_skills or "") if t.strip()]
    for tech in input_techs:
        result[f"{tech}_Projects"] = "N/A"
        result[f"{tech}_Score"] = 0
    result["GitHub Average Probability"] = 0

    gh_info = extract_github_info_via_ai(resume_text, links, api_key)
    if gh_info.get("github_found") and gh_info.get("github_username"):
        gh = analyze_github_repositories(gh_info["github_username"], github_skills, _next_token())
        result["GitHub Repo Count"] = gh.get("total_public_repos", 0)
        if gh.get("found"):
            for tech, data in gh.get("tech_details", {}).items():
                prefix = tech.upper()
                result[f"{prefix}_Projects"] = "\n".join(data["projects"]) if data["projects"] else "N/A"
                result[f"{prefix}_Score"] = data["score"]
            result["GitHub Average Probability"] = gh.get("github_average_probability", 0)
            result["GitHub Screening Outcome"] = "Analysis Complete"
            result["Ownership"] = "Yes (Verified)" if gh.get("commits_verified") else "No"
        else:
            result["GitHub Screening Outcome"] = gh.get("error", "Error")
        result["Profile Used"] = gh_info.get("github_url") or gh_info.get("github_username")
    else:
        result["GitHub Screening Outcome"] = "Profile Not Found"

    return result
