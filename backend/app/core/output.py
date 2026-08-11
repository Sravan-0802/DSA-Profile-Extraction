"""Column ordering, filtering, and CSV serialization for results."""
from __future__ import annotations

import csv
import io
from typing import Any, Optional

from ..constants import DSA_COLUMNS, SKILL_COLUMNS


def _num(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def order_columns(results: list[dict[str, Any]]) -> list[str]:
    """Build a stable column order: known leading columns first, rest appended."""
    leading = [
        "User ID", "Resume Link", "Company Name",
        "Priority Band", "Overall Probability", "Overall Remarks",
        "Skills Probability", "Skills Remarks",
        "Projects Probability", "Projects Remarks",
        "Experience Probability", "Experience Remarks",
        "Other Probability", "Other Remarks",
        "Full Name", "Mobile Number", "Email ID", "City", "State",
        "LinkedIn Link", "GitHub Link", "Other Links", "GitHub Repo Count",
        "Skills",
        "Total Projects Count", "Internal Projects Count", "External Projects Count",
        "Internal Project Title", "Internal Projects Techstacks",
        "External Project Title", "External Projects Techstacks",
        "Internal Project Titles", "Internal Project Techstacks",
        "External Project Titles", "External Project Techstacks",
    ]
    seen = set()
    ordered: list[str] = []
    for col in leading + SKILL_COLUMNS + DSA_COLUMNS:
        if col not in seen:
            seen.add(col)
            ordered.append(col)

    # Append any remaining keys that appear in the data, preserving first-seen order.
    tail: list[str] = []
    for row in results:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                tail.append(key)
    # keep Error / Analysis Datetime at the very end if present
    enders = [c for c in ("Error", "Analysis Datetime") if c in tail]
    tail = [c for c in tail if c not in enders]

    present = [c for c in ordered if any(c in r for r in results)]
    return present + tail + enders


def apply_filters(results: list[dict[str, Any]], f: Optional[dict[str, Any]]) -> list[dict[str, Any]]:
    if not f:
        return results
    out = results

    bands = f.get("priority_bands")
    if bands:
        out = [r for r in out if r.get("Priority Band") in bands]

    search = (f.get("search") or "").strip().lower()
    if search:
        fields = ("Skills", "Overall Remarks", "Internal Project Title", "External Project Title", "Full Name")
        out = [r for r in out if any(search in str(r.get(fld, "")).lower() for fld in fields)]

    ranges = {
        "Overall Probability": ("overall_min", "overall_max"),
        "Skills Probability": ("skills_min", "skills_max"),
        "Experience Probability": ("experience_min", "experience_max"),
        "Projects Probability": ("projects_min", "projects_max"),
        "Other Probability": ("other_min", "other_max"),
    }
    for col, (lo_key, hi_key) in ranges.items():
        lo, hi = f.get(lo_key), f.get(hi_key)
        if lo is not None:
            out = [r for r in out if _num(r.get(col, 0)) >= lo]
        if hi is not None:
            out = [r for r in out if _num(r.get(col, 0)) <= hi]

    for col, key in (
        ("Total Projects Count", "min_total_projects"),
        ("Internal Projects Count", "min_internal_projects"),
        ("External Projects Count", "min_external_projects"),
    ):
        val = f.get(key)
        if val:
            out = [r for r in out if _num(r.get(col, 0)) >= val]

    if f.get("only_internal"):
        out = [r for r in out if _num(r.get("Internal Projects Count", 0)) > 0]
    if f.get("only_external"):
        out = [r for r in out if _num(r.get("External Projects Count", 0)) > 0]

    return out


def to_csv(results: list[dict[str, Any]]) -> str:
    columns = order_columns(results)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in results:
        writer.writerow({c: row.get(c, "") for c in columns})
    return buf.getvalue()
