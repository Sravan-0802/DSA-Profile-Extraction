"""Resume analysis: shortlisting and comprehensive extraction modes.

Ported from the Streamlit Resume-analyzer worker functions, refactored so
text extraction happens once and the extracted text is passed in.
"""
from __future__ import annotations

import logging
import re

import requests

from ..constants import SKILL_COLUMNS, SKILLS_TO_ASSESS
from .ai import analyze_text_with_mistral
from .projects import (
    classify_and_format_projects,
    get_internal_projects_string,
    project_instruction_block,
)
from .utils import (
    assign_priority_band,
    format_mobile_number,
    extract_github_username,
    is_present_str,
    relaxed_json_loads,
    safe_str,
    sort_links,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_github_repo_count(username: str | None) -> str:
    if not username:
        return ""
    try:
        resp = requests.get(f"https://api.github.com/users/{username}", timeout=10)
        if resp.status_code == 200:
            return str(resp.json().get("public_repos", ""))
    except requests.RequestException:
        pass
    return ""


def get_latest_experience(exp_list):
    if not isinstance(exp_list, list) or not exp_list:
        return None
    for exp in exp_list:
        if isinstance(exp, dict) and is_present_str(exp.get("endDate", "")):
            return exp
    for exp in exp_list:
        if isinstance(exp, dict):
            return exp
    return None


def get_highest_education_institute(edu) -> str:
    if not isinstance(edu, dict):
        return ""
    for level in ("masters_doctorate", "bachelors", "diploma", "intermediate_puc_12th", "ssc_10th"):
        data = edu.get(level)
        if isinstance(data, dict) and safe_str(data.get("collegeName")):
            return safe_str(data["collegeName"])
    return ""


def calculate_skill_probabilities(data: dict) -> dict[str, int]:
    scores = {col: 0 for col in SKILL_COLUMNS}
    if not isinstance(data, dict):
        return scores

    skills_list = data.get("skills", []) if isinstance(data.get("skills"), list) else []
    skills_text = " ".join(safe_str(x) for x in skills_list).lower()

    projects = data.get("projects", [])
    projects_text = " ".join(safe_str(x) for x in projects).lower() if isinstance(projects, list) else safe_str(projects).lower()

    certs = data.get("certifications", [])
    certs_text = " ".join(safe_str(x) for x in certs).lower() if isinstance(certs, list) else safe_str(certs).lower()

    exp_list = data.get("experience", [])
    if isinstance(exp_list, list):
        chunks = []
        for exp in exp_list:
            if isinstance(exp, dict):
                desc = exp.get("description", "")
                chunks.append(" ".join(safe_str(x) for x in desc) if isinstance(desc, list) else safe_str(desc))
                chunks.append(safe_str(exp.get("jobTitle", "")))
                chunks.append(safe_str(exp.get("companyName", "")))
        experience_text = " ".join(chunks).lower()
    else:
        experience_text = safe_str(exp_list).lower()

    education_text = safe_str(data.get("education", {})).lower()
    foundational = f"{skills_text} {projects_text} {experience_text} {education_text}"

    for skill in SKILLS_TO_ASSESS:
        if skill == ".Net":
            pattern = r"(?i)(?<![a-zA-Z0-9])\.net(?![a-zA-Z0-9])"
        else:
            pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        score = 0
        if re.search(pattern, foundational):
            score += 10
        if re.search(pattern, experience_text):
            score += 30
        if re.search(pattern, projects_text):
            score += 20
        if re.search(pattern, certs_text):
            score += 20
        scores[f"{skill}_Probability"] = score
    return scores


# ---------------------------------------------------------------------------
# Shortlisting
# ---------------------------------------------------------------------------
def analyze_shortlisting(
    resume_text: str, user_requirements: str, shortlisting_mode: str, api_key: str
) -> dict:
    result = {
        "Overall Probability": 0, "Overall Remarks": "Error processing",
        "Projects Probability": 0, "Projects Remarks": "",
        "Skills Probability": 0, "Skills Remarks": "",
        "Experience Probability": 0, "Experience Remarks": "",
        "Other Probability": 0, "Other Remarks": "",
        "Internal Project Title": "", "Internal Projects Techstacks": "",
        "External Project Title": "", "External Projects Techstacks": "",
        "Total Projects Count": 0, "Internal Projects Count": 0, "External Projects Count": 0,
    }

    internal_str = get_internal_projects_string()

    # Java-vs-JavaScript anti-hallucination guard.
    system_warning = ""
    reqs_lower = user_requirements.lower()
    if re.search(r"\bjava\b", reqs_lower) and not re.search(r"\bjava\b", resume_text.lower()):
        system_warning = (
            "\n\n[SYSTEM WARNING]: The user explicitly requires 'Java' (the backend "
            "language). 'Java' appears MISSING as a standalone word. 'JavaScript' is NOT "
            "Java. Treat 'Java' as MISSING."
        )

    prompt = f"""
You are a Nuanced Technical Recruiter and Logic Engine.
Categorize the candidate into Priority Bands (P1, P2, P3) based on strict keyword matching.
{system_warning}

**CRITICAL ANTI-HALLUCINATION RULES:**
1. JAVA IS NOT JAVASCRIPT. If the resume contains "JavaScript"/"React.js", do NOT count it as "Java".
   If the resume text does not explicitly say "Java" as a separate word, count it as MISSING.

**SCORING GUIDELINES:**
- BAND P1 (90-100): Candidate has ALL required technologies.
- BAND P2 (75-89): Matches MOST criteria, missing 1-2 specific technologies.
- BAND P3 (60-74): Has relevant skills but missing MAJOR parts of the stack.
- BAND F (0-59): Resume is unrelated to the requirements.

Return a single, pure JSON object:
{{
  "projects_probability": "integer (0-100)", "projects_remarks": "string",
  "skills_probability": "integer (0-100)", "skills_remarks": "string",
  "experience_probability": "integer (0-100)", "experience_remarks": "string",
  "other_probability": "integer (0-100)", "other_remarks": "string",
  "overall_probability": "integer (0-100)", "overall_remarks": "string",
  {project_instruction_block(internal_str)}
}}

---
**Required Criteria:**
{user_requirements}
---
**Resume Text:**
{resume_text}
---
"""
    response = analyze_text_with_mistral(prompt, api_key)
    data = relaxed_json_loads(response)
    if not isinstance(data, dict):
        raise ValueError("AI returned non-object response.")
    if "error" in data:
        raise ValueError(safe_str(data["error"]))

    result.update({
        "Overall Probability": data.get("overall_probability", 0),
        "Projects Probability": data.get("projects_probability", 0),
        "Skills Probability": data.get("skills_probability", 0),
        "Experience Probability": data.get("experience_probability", 0),
        "Other Probability": data.get("other_probability", 0),
        "Overall Remarks": safe_str(data.get("overall_remarks", "N/A")),
        "Projects Remarks": safe_str(data.get("projects_remarks", "N/A")),
        "Skills Remarks": safe_str(data.get("skills_remarks", "N/A")),
        "Experience Remarks": safe_str(data.get("experience_remarks", "N/A")),
        "Other Remarks": safe_str(data.get("other_remarks", "N/A")),
    })

    classified = classify_and_format_projects(data.get("projects", []))
    result.update(classified)
    internal_count = len(classified["Internal Project Title"].splitlines()) if classified["Internal Project Title"] else 0
    external_count = len(classified["External Project Title"].splitlines()) if classified["External Project Title"] else 0
    result["Internal Projects Count"] = internal_count
    result["External Projects Count"] = external_count
    result["Total Projects Count"] = internal_count + external_count

    if shortlisting_mode == "Priority Wise (P1 / P2 / P3 Bands)":
        result["Priority Band"] = assign_priority_band(result.get("Overall Probability", 0))

    return result


# ---------------------------------------------------------------------------
# Comprehensive extraction
# ---------------------------------------------------------------------------
def _build_extraction_prompt(analysis_type: str, resume_text: str, internal_str: str) -> str:
    block = project_instruction_block(internal_str)
    if analysis_type == "Internal Projects Matching":
        return f"""
You are a project classification expert. From the resume text:
1. Extract all projects.
2. Classify each as "Internal" (matches the OFFICIAL INTERNAL PROJECTS LIST, flexible matching)
   or "External".
Return ONLY a pure JSON object.
OFFICIAL INTERNAL PROJECTS LIST:
---
{internal_str}
---
Structure: {{ "projects": [ {{ "title": "string", "techStack": ["..."], "classification": "Internal" or "External" }} ] }}
Resume Text:
---
{resume_text}
---
"""
    if analysis_type == "Personal Details":
        return f"""
Extract ONLY personal details into a pure JSON object. Response MUST be only the JSON.
Structure: {{"fullName": "string", "mobileNumber": "string", "email": "string", "address": {{"city": "string", "state": "string"}}, "textLinks": ["list of strings"]}}
Resume Text: --- {resume_text} ---
"""
    if analysis_type == "Skills & Projects":
        return f"""
You are an expert data extractor. Produce a single JSON object.
{{
  "skills": ["list of strings"], "certifications": ["list of strings"],
  "awards": ["list of strings"], "achievements": ["list of strings"],
  {block}
  "experience": [{{ "companyName": "string", "jobTitle": "string", "startDate": "string", "endDate": "string", "description": "string"}}]
}}
Resume Text:
---
{resume_text}
---
"""
    # "All Data"
    return f"""
You are a machine that strictly outputs a single, valid JSON object. Analyze the resume text.
{{
  "fullName": "string", "mobileNumber": "string", "email": "string",
  "address": {{"city": "string", "state": "string"}}, "textLinks": ["list of all URLs found"],
  "skills": ["list of strings"], "certifications": ["list of strings"], "awards": ["list of strings"],
  "achievements": ["list of strings"], "yearsITExperience": "float or string", "yearsNonITExperience": "float or string",
  {block}
  "education": {{
    "masters_doctorate": {{"courseName": "string", "departmentName": "string", "completionYear": "string", "percentage": "string", "collegeName": "string"}},
    "bachelors": {{"courseName": "string", "departmentName": "string", "completionYear": "string", "percentage": "string", "collegeName": "string"}},
    "diploma": {{"courseName": "string", "departmentName": "string", "completionYear": "string", "percentage": "string", "collegeName": "string"}},
    "intermediate_puc_12th": {{"schoolName": "string", "departmentName": "string", "completionYear": "string", "percentage": "string", "collegeName": "string"}},
    "ssc_10th": {{"schoolName": "string", "completionYear": "string", "percentage": "string", "collegeName": "string"}}
  }},
  "experience": [ {{ "companyName": "string", "jobTitle": "string", "startDate": "string", "endDate": "string", "description": "string or list of strings" }} ]
}}
Resume Text:
---
{resume_text}
---
"""


def analyze_comprehensive(
    resume_text: str, clickable_links: list[str], analysis_type: str, api_key: str
) -> dict:
    internal_str = get_internal_projects_string()
    prompt = _build_extraction_prompt(analysis_type, resume_text, internal_str)
    response = analyze_text_with_mistral(prompt, api_key)
    data = relaxed_json_loads(response)
    if not isinstance(data, dict):
        raise ValueError("AI returned non-object response.")
    if "error" in data:
        raise ValueError(safe_str(data["error"]))

    result: dict = {}
    classified = classify_and_format_projects(data.get("projects", []))

    if analysis_type == "Internal Projects Matching":
        internal_count = len(classified["Internal Project Title"].splitlines()) if classified["Internal Project Title"] else 0
        external_count = len(classified["External Project Title"].splitlines()) if classified["External Project Title"] else 0
        result.update({
            "Total Projects Count": internal_count + external_count,
            "Internal Projects Count": internal_count,
            "External Projects Count": external_count,
            "Internal Project Titles": classified["Internal Project Title"],
            "Internal Project Techstacks": classified["Internal Projects Techstacks"],
            "External Project Titles": classified["External Project Title"],
            "External Project Techstacks": classified["External Projects Techstacks"],
        })
        return result

    result.update(classified)

    if analysis_type in ("All Data", "Personal Details"):
        addr = data.get("address", {}) if isinstance(data.get("address"), dict) else {}
        result.update({
            "Full Name": safe_str(data.get("fullName", "")),
            "Mobile Number": format_mobile_number(data.get("mobileNumber", "")),
            "Email ID": safe_str(data.get("email", "")),
            "City": safe_str(addr.get("city", "")),
            "State": safe_str(addr.get("state", "")),
        })
        text_links = data.get("textLinks", [])
        if not isinstance(text_links, list):
            text_links = [safe_str(text_links)] if text_links else []
        all_links = sorted(set([safe_str(x) for x in text_links] + list(clickable_links)))
        linkedin, github, others = sort_links(all_links)
        result.update({"LinkedIn Link": linkedin, "GitHub Link": github, "Other Links": "\n".join(others)})
        if github:
            result["GitHub Repo Count"] = get_github_repo_count(extract_github_username(github))

    if analysis_type in ("All Data", "Skills & Projects"):
        result.update(calculate_skill_probabilities(data))
        skills = data.get("skills", [])
        if isinstance(skills, list):
            result["Skills"] = ", ".join(sorted({safe_str(s) for s in skills if safe_str(s)}))
        for key, col in (("certifications", "Certifications"), ("awards", "Awards"), ("achievements", "Achievements")):
            vals = data.get(key, [])
            if isinstance(vals, list):
                result[col] = "\n".join(safe_str(v) for v in vals if safe_str(v))
        latest = get_latest_experience(data.get("experience", []))
        if latest:
            end_date = latest.get("endDate", "")
            result.update({
                "Latest Experience Company Name": safe_str(latest.get("companyName", "")),
                "Latest Experience Job Title": safe_str(latest.get("jobTitle", "")),
                "Latest Experience Start Date": safe_str(latest.get("startDate", "")),
                "Latest Experience End Date": safe_str(end_date),
                "Currently Working? (Yes/No)": "Yes" if is_present_str(end_date) else "No",
            })

    if analysis_type == "All Data":
        result.update({
            "Years of IT Experience": safe_str(data.get("yearsITExperience", "")),
            "Years of Non-IT Experience": safe_str(data.get("yearsNonITExperience", "")),
        })
        edu = data.get("education", {}) if isinstance(data.get("education"), dict) else {}
        result["Highest Education Institute Name"] = get_highest_education_institute(edu)
        edu_levels = {
            "masters_doctorate": ("Masters/Doctorate", "courseName"),
            "bachelors": ("Bachelors", "courseName"),
            "diploma": ("Diploma", "courseName"),
            "intermediate_puc_12th": ("Intermediate / PUC / 12th", "schoolName"),
            "ssc_10th": ("SSC / 10th", "schoolName"),
        }
        for key, (prefix, name_key) in edu_levels.items():
            level = edu.get(key, {}) if isinstance(edu.get(key), dict) else {}
            if key in ("intermediate_puc_12th", "ssc_10th"):
                result[f"{prefix} Name"] = safe_str(level.get(name_key, ""))
            result[f"{prefix} Course Name"] = safe_str(level.get("courseName", ""))
            result[f"{prefix} College Name"] = safe_str(level.get("collegeName", ""))
            result[f"{prefix} Department Name"] = safe_str(level.get("departmentName", ""))
            result[f"{prefix} Year of Completion"] = safe_str(level.get("completionYear", ""))
            result[f"{prefix} Percentage"] = safe_str(level.get("percentage", ""))

    return result
