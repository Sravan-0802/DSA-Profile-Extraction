"""Shared helpers: string sanitization, robust JSON parsing, formatting."""
from __future__ import annotations

import json
import re
from typing import Any

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def safe_str(x: Any) -> str:
    """Convert any value to a clean string without control characters."""
    try:
        s = str(x) if x is not None else ""
    except Exception:
        s = ""
    return _CONTROL_CHARS_RE.sub("", s)


def is_present_str(s: Any) -> bool:
    """Forgiving check for 'currently working' style end-dates."""
    if s is None:
        return False
    low = safe_str(s).lower()
    return "present" in low or "current" in low


def sanitize_json_text(text: str) -> str:
    """Clean a model response down to a parseable JSON object/array.

    Strips markdown fences and surrounding prose, isolates the JSON span,
    removes control chars, escapes stray backslashes, and best-effort closes
    unterminated strings / unbalanced braces & brackets.
    """
    if not isinstance(text, str):
        text = str(text)
    text = text.strip()

    first_brace = text.find("{")
    first_bracket = text.find("[")
    if first_brace == -1 and first_bracket == -1:
        return '{"error": "No valid JSON object or array found in response"}'

    if first_brace != -1 and first_bracket != -1:
        start = min(first_brace, first_bracket)
    elif first_brace != -1:
        start = first_brace
    else:
        start = first_bracket

    end = max(text.rfind("}"), text.rfind("]"))
    if end < start:
        return '{"error": "No valid JSON structure found in response"}'

    text = text[start : end + 1]
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)
    text = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", text)

    if text.count('"') % 2 != 0:
        text += '"'

    open_braces, close_braces = text.count("{"), text.count("}")
    if open_braces > close_braces:
        text += "}" * (open_braces - close_braces)

    open_brackets, close_brackets = text.count("["), text.count("]")
    if open_brackets > close_brackets:
        text += "]" * (open_brackets - close_brackets)

    return text


def relaxed_json_loads(text: str) -> dict:
    """Parse JSON robustly after sanitization. Raises on hard failure."""
    return json.loads(sanitize_json_text(text))


def assign_priority_band(probability: Any) -> str:
    """Map an overall probability score to a priority band."""
    try:
        prob = float(probability)
    except (ValueError, TypeError):
        return "Not Shortlisted"
    if prob >= 90:
        return "P1"
    if 75 <= prob < 90:
        return "P2"
    if 60 <= prob < 75:
        return "P3"
    return "Not Shortlisted"


def format_mobile_number(raw_number: Any) -> str:
    """Normalize a phone number to a bare 10-digit form where possible."""
    raw = safe_str(raw_number)
    if not raw.strip():
        return ""
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        return digits[1:]
    if len(digits) == 10:
        return digits
    return ""


def extract_github_username(url: str) -> str | None:
    match = re.search(r"github\.com/([^/]+)", url or "")
    return match.group(1) if match else None


def sort_links(links: list[str]) -> tuple[str, str, list[str]]:
    """Split a link list into (linkedin, github, others)."""
    linkedin, github = "", ""
    others: list[str] = []
    for link in links:
        link = safe_str(link)
        if "linkedin.com/in/" in link and not linkedin:
            linkedin = link
        elif "github.com" in link and not github:
            github = link
        else:
            others.append(link)
    if github:
        username = extract_github_username(github)
        if username:
            github = f"https://github.com/{username}"
    return linkedin, github, others
