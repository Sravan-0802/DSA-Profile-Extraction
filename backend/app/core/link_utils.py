"""Categorize resume links into coding-platform profiles.

Ported from the original DSA Extractor's link_utils.py.
"""
from __future__ import annotations

import re

PLATFORMS = ["github", "leetcode", "codeforces", "codechef", "hackerrank"]
INVALID_WORDS = ["solved", "problem", "rating", "contest"]


def clean_text(text: str) -> str:
    text = (text or "").lower()
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text


def extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://[^\s]+", text or "")


def validate_github(url: str):
    return re.match(r"https?://(www\.)?github\.com/[a-zA-Z0-9_-]+/?$", url)


def validate_leetcode(url: str):
    return re.match(r"https?://(www\.)?leetcode\.com/(u/)?[a-zA-Z0-9_-]+/?$", url)


def validate_codeforces(url: str):
    return re.match(r"https?://(www\.)?codeforces\.com/profile/[a-zA-Z0-9_-]+/?$", url)


def validate_codechef(url: str):
    return re.match(r"https?://(www\.)?codechef\.com/users/[a-zA-Z0-9_-]+/?$", url)


def validate_hackerrank(url: str):
    return re.match(r"https?://(www\.)?hackerrank\.com/[a-zA-Z0-9_-]+/?$", url)


_VALIDATORS = {
    "github": validate_github,
    "leetcode": validate_leetcode,
    "codeforces": validate_codeforces,
    "codechef": validate_codechef,
    "hackerrank": validate_hackerrank,
}


def normalize_profile_url(url: str, platform: str) -> str:
    """Return a cleaned profile URL if it matches *platform*, else \"\"."""
    url = (url or "").strip().split()[0].rstrip(".,);]")
    if not url:
        return ""
    # Allow bare usernames in a platform column: "Achal_Sayee"
    if "://" not in url and re.fullmatch(r"[a-zA-Z0-9_-]+", url):
        base = {
            "github": "https://github.com/{}",
            "leetcode": "https://leetcode.com/u/{}",
            "codeforces": "https://codeforces.com/profile/{}",
            "codechef": "https://www.codechef.com/users/{}",
            "hackerrank": "https://www.hackerrank.com/{}",
        }.get(platform)
        return base.format(url) if base else ""
    validator = _VALIDATORS.get(platform)
    if not validator:
        return ""
    candidate = url.rstrip("/")
    if validator(candidate) or validator(candidate + "/"):
        return candidate
    return ""


def extract_usernames(text: str) -> dict[str, str]:
    usernames: dict[str, str] = {}
    patterns = {
        "github": r"github\s*[:\-]\s*([a-zA-Z0-9_-]+)",
        "leetcode": r"leetcode\s*[:\-]\s*([a-zA-Z0-9_-]+)",
        "codeforces": r"codeforces\s*[:\-]\s*([a-zA-Z0-9_-]+)",
        "codechef": r"codechef\s*[:\-]\s*([a-zA-Z0-9_-]+)",
        "hackerrank": r"hackerrank\s*[:\-]\s*([a-zA-Z0-9_-]+)",
    }
    for platform, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            usernames[platform] = match.group(1)
    return usernames


def categorize_links(text: str, urls: list[str]) -> dict[str, str]:
    """Return a dict mapping each platform to its profile URL ("" if none)."""
    text = clean_text(text)
    usernames = extract_usernames(text)

    profiles = {p: "" for p in PLATFORMS}

    for url in urls:
        url = url.split("|")[0].strip()
        if any(word in url.lower() for word in INVALID_WORDS):
            continue
        if validate_github(url):
            profiles["github"] = url
        elif validate_leetcode(url):
            profiles["leetcode"] = url
        elif validate_codeforces(url):
            profiles["codeforces"] = url
        elif validate_codechef(url):
            profiles["codechef"] = url
        elif validate_hackerrank(url):
            profiles["hackerrank"] = url

    # Fall back to "platform: username" mentions in the text.
    base = {
        "github": "https://github.com/{}",
        "leetcode": "https://leetcode.com/{}",
        "codeforces": "https://codeforces.com/profile/{}",
        "codechef": "https://codechef.com/users/{}",
        "hackerrank": "https://hackerrank.com/{}",
    }
    for platform, tmpl in base.items():
        if not profiles[platform] and platform in usernames:
            profiles[platform] = tmpl.format(usernames[platform])

    return profiles
