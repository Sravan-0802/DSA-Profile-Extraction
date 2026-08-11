"""Analysis modes, skill list, and column ordering definitions."""
from __future__ import annotations

# ---- Analysis modes -------------------------------------------------------
ANALYSIS_TYPES = [
    "All Data",
    "Personal Details",
    "Skills & Projects",
    "Internal Projects Matching",
]

SHORTLISTING_MODES = [
    "Probability Wise (Default)",
    "Priority Wise (P1 / P2 / P3 Bands)",
]

# ---- Skills assessed for probability scoring ------------------------------
SKILLS_TO_ASSESS = [
    "JavaScript", "Python", "Node", "React", "Java", "Springboot", "DSA",
    "AI", "ML", "PHP", ".Net", "Testing", "AWS", "Django", "PowerBI", "Tableau",
]
SKILL_COLUMNS = [f"{skill}_Probability" for skill in SKILLS_TO_ASSESS]

# ---- DSA coding-platform columns (from the DSA Extractor tool) ------------
DSA_PLATFORMS = ["github", "leetcode", "codeforces", "codechef", "hackerrank"]
DSA_COLUMNS = [
    "GitHub Profile", "LeetCode Profile", "Codeforces Profile",
    "CodeChef Profile", "HackerRank Profile",
    "LeetCode Solved", "Codeforces Solved", "CodeChef Solved",
]

# ---- Priority bands -------------------------------------------------------
PRIORITY_ORDER = ["P1", "P2", "P3", "Not Shortlisted"]
