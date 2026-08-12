"""Fetch coding-platform profile metrics for DSA mode.

Sources:
  - LeetCode: public GraphQL API
  - Codeforces: public REST API
  - CodeChef: public profile HTML (light scrape)

Fields that platforms do not expose publicly are left blank ("").
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

_UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# Codeforces problem rating bands (common recruiting heuristic).
_CF_MEDIUM_MIN = 1400
_CF_HARD_MIN = 2100

_SIX_MONTHS = timedelta(days=182)


def get_username(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def _blank_leetcode() -> dict[str, object]:
    return {
        "LeetCode Level": "",
        "LeetCode Contest Rating": "",
        "LeetCode Solved": 0,
        "LeetCode Medium Solved": 0,
        "LeetCode Hard Solved": 0,
        # Unique AC solves over 6 months are not fully exposed; this is
        # submission activity from the public calendar.
        "LeetCode Submissions (Last 6 Months)": 0,
    }


def _blank_codeforces() -> dict[str, object]:
    return {
        "Codeforces Rating": "",
        "Codeforces Max Rating": "",
        "Codeforces Rank": "",
        # Global contest percentile is not provided by the public API.
        "Codeforces Contest Percentile": "",
        "Codeforces Solved": 0,
        "Codeforces Medium Solved": 0,
        "Codeforces Hard Solved": 0,
        "Codeforces Solved (Last 6 Months)": 0,
        "Codeforces Contest Problems Solved": 0,
    }


def _blank_codechef() -> dict[str, object]:
    return {
        "CodeChef Rating": "",
        "CodeChef Division": "",
        "CodeChef Solved": 0,
        # Difficulty breakdown is not published on the public profile page.
        "CodeChef Medium Solved": "",
        "CodeChef Hard Solved": "",
        "CodeChef Solved (Last 6 Months)": "",
        "CodeChef Contests Participated": "",
    }


def fetch_leetcode_stats(username: str) -> dict[str, object]:
    out = _blank_leetcode()
    query = """
    query ($username: String!) {
      matchedUser(username: $username) {
        submitStatsGlobal {
          acSubmissionNum { difficulty count }
        }
        userCalendar { submissionCalendar }
      }
      userContestRanking(username: $username) {
        rating
        topPercentage
        badge { name }
      }
    }
    """
    try:
        res = requests.post(
            "https://leetcode.com/graphql",
            json={"query": query, "variables": {"username": username}},
            headers=_UA,
            timeout=15,
        )
        data = res.json().get("data") or {}
        user = data.get("matchedUser")
        if not user:
            return out

        counts = {
            row["difficulty"]: int(row["count"])
            for row in (user.get("submitStatsGlobal") or {}).get("acSubmissionNum") or []
        }
        out["LeetCode Solved"] = counts.get("All", 0)
        out["LeetCode Medium Solved"] = counts.get("Medium", 0)
        out["LeetCode Hard Solved"] = counts.get("Hard", 0)

        contest = data.get("userContestRanking") or {}
        if contest.get("rating") is not None:
            out["LeetCode Contest Rating"] = round(float(contest["rating"]))
        badge = (contest.get("badge") or {}).get("name") or ""
        out["LeetCode Level"] = badge

        cal_raw = (user.get("userCalendar") or {}).get("submissionCalendar") or "{}"
        try:
            calendar = json.loads(cal_raw)
        except json.JSONDecodeError:
            calendar = {}
        cutoff = int((datetime.now(timezone.utc) - _SIX_MONTHS).timestamp())
        out["LeetCode Submissions (Last 6 Months)"] = sum(
            int(v) for k, v in calendar.items() if int(k) >= cutoff
        )
    except Exception:
        pass
    return out


def _cf_get(url: str, *, retries: int = 4) -> dict | None:
    for attempt in range(retries):
        try:
            res = requests.get(url, timeout=25)
            data = res.json()
            if data.get("status") == "OK":
                return data
            comment = (data.get("comment") or "").lower()
            if "not found" in comment and "limit exceeded" not in comment:
                return None
        except Exception:
            pass
        if attempt < retries - 1:
            time.sleep(2 * (attempt + 1))
    return None


def fetch_codeforces_stats(username: str) -> dict[str, object]:
    out = _blank_codeforces()

    info = _cf_get(f"https://codeforces.com/api/user.info?handles={username}")
    if info and info.get("result"):
        u = info["result"][0]
        if "rating" in u:
            out["Codeforces Rating"] = u["rating"]
        if "maxRating" in u:
            out["Codeforces Max Rating"] = u["maxRating"]
        if u.get("rank"):
            out["Codeforces Rank"] = u["rank"]

    # Pace CF calls — public API is ~1 req / 2s.
    time.sleep(1.2)

    status = _cf_get(f"https://codeforces.com/api/user.status?handle={username}")
    if not status:
        return out

    cutoff = int((datetime.now(timezone.utc) - _SIX_MONTHS).timestamp())
    first_ac_ts: dict[tuple, int] = {}
    problem_rating: dict[tuple, int | None] = {}
    contest_solved: set[tuple] = set()

    for sub in status.get("result") or []:
        if sub.get("verdict") != "OK":
            continue
        problem = sub.get("problem") or {}
        key = (problem.get("contestId"), problem.get("index"))
        if key[0] is None and key[1] is None:
            continue
        ts = int(sub.get("creationTimeSeconds") or 0)
        if key not in first_ac_ts or ts < first_ac_ts[key]:
            first_ac_ts[key] = ts
            problem_rating[key] = problem.get("rating")
        ptype = (sub.get("author") or {}).get("participantType") or ""
        if ptype in {"CONTESTANT", "VIRTUAL", "OUT_OF_COMPETITION"}:
            contest_solved.add(key)

    medium = hard = last6 = 0
    for key, ts in first_ac_ts.items():
        rating = problem_rating.get(key)
        if isinstance(rating, int):
            if rating >= _CF_HARD_MIN:
                hard += 1
            elif rating >= _CF_MEDIUM_MIN:
                medium += 1
        if ts >= cutoff:
            last6 += 1

    out["Codeforces Solved"] = len(first_ac_ts)
    out["Codeforces Medium Solved"] = medium
    out["Codeforces Hard Solved"] = hard
    out["Codeforces Solved (Last 6 Months)"] = last6
    out["Codeforces Contest Problems Solved"] = len(contest_solved)
    return out


def fetch_codechef_stats(username: str) -> dict[str, object]:
    out = _blank_codechef()
    try:
        res = requests.get(
            f"https://www.codechef.com/users/{username}",
            headers=_UA,
            timeout=15,
        )
        soup = BeautifulSoup(res.text, "lxml")
        text = soup.get_text("\n", strip=True)

        match = re.search(r"Total Problems Solved:\s*(\d+)", text)
        if match:
            out["CodeChef Solved"] = int(match.group(1))
        else:
            match = re.search(r"Fully Solved\s*\((\d+)\)", text)
            if match:
                out["CodeChef Solved"] = int(match.group(1))

        # Rating + division from the rating header when the user is rated.
        header = soup.select_one("div.rating-header")
        header_text = header.get_text(" ", strip=True) if header else ""
        rating_el = soup.select_one(".rating-number")
        if rating_el:
            rating_txt = rating_el.get_text(strip=True)
            if rating_txt.isdigit():
                out["CodeChef Rating"] = int(rating_txt)
        if not out["CodeChef Rating"] and header_text:
            m = re.search(r"\b(\d{3,4})\b", header_text)
            if m:
                out["CodeChef Rating"] = int(m.group(1))

        div_match = re.search(r"\(Div\s*([12])\)", header_text, re.I)
        if div_match:
            out["CodeChef Division"] = f"Div {div_match.group(1)}"
        elif header_text:
            # Fallback: some pages say "Division 1" in nearby text.
            div_match = re.search(r"Division\s*([12])", header_text, re.I)
            if div_match:
                out["CodeChef Division"] = f"Div {div_match.group(1)}"

        contests = re.search(r"Contests\s*\((\d+)\)", text)
        if contests:
            out["CodeChef Contests Participated"] = int(contests.group(1))
    except Exception:
        pass
    return out


def collect_dsa_stats(profiles: dict[str, str]) -> dict[str, object]:
    """Given categorized profile URLs, return the DSA output columns."""
    out: dict[str, object] = {
        "GitHub Profile": profiles.get("github", ""),
        "LeetCode Profile": profiles.get("leetcode", ""),
        "Codeforces Profile": profiles.get("codeforces", ""),
        "CodeChef Profile": profiles.get("codechef", ""),
        "HackerRank Profile": profiles.get("hackerrank", ""),
    }
    out.update(_blank_leetcode())
    out.update(_blank_codeforces())
    out.update(_blank_codechef())

    if profiles.get("leetcode"):
        out.update(fetch_leetcode_stats(get_username(profiles["leetcode"])))
    if profiles.get("codeforces"):
        out.update(fetch_codeforces_stats(get_username(profiles["codeforces"])))
    # CodeChef scraping feature temporarily disabled in the UI.
    # Backend scrape (fetch_codechef_stats) is kept intact for later re-enable.
    if profiles.get("codechef"):
        out.update(fetch_codechef_stats(get_username(profiles["codechef"])))
    return out
