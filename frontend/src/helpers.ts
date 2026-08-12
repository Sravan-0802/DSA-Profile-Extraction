import type { FilterState, Row } from "./types";
import { isCodechefColumn } from "./codechefGate";

const SKILL_SUFFIX = "_Probability";

const LEADING = [
  "User ID", "Resume Link", "Company Name",
  "Priority Band", "Overall Probability", "Overall Remarks",
  "Skills Probability", "Skills Remarks",
  "Projects Probability", "Projects Remarks",
  "Experience Probability", "Experience Remarks",
  "Other Probability", "Other Remarks",
  "Full Name", "Mobile Number", "Email ID", "City", "State",
  "LinkedIn Link", "GitHub Link", "Other Links", "GitHub Repo Count", "Skills",
  "Total Projects Count", "Internal Projects Count", "External Projects Count",
  "Internal Project Title", "Internal Projects Techstacks",
  "External Project Title", "External Projects Techstacks",
  "Internal Project Titles", "Internal Project Techstacks",
  "External Project Titles", "External Project Techstacks",
  // CodeChef scraping feature temporarily disabled — "CodeChef Profile" and "CodeChef Solved" removed from column ordering
  "GitHub Profile", "LeetCode Profile", "Codeforces Profile", /* "CodeChef Profile", */ "HackerRank Profile",
  "LeetCode Solved", "Codeforces Solved", /* "CodeChef Solved", */
];

export function orderColumns(rows: Row[]): string[] {
  const present = new Set<string>();
  rows.forEach((r) => Object.keys(r).forEach((k) => present.add(k)));

  const ordered: string[] = [];
  const seen = new Set<string>();
  const push = (k: string) => {
    // CodeChef scraping feature temporarily disabled — never show CodeChef columns in the UI table.
    if (isCodechefColumn(k)) return;
    if (present.has(k) && !seen.has(k)) {
      seen.add(k);
      ordered.push(k);
    }
  };

  LEADING.forEach(push);
  // skill probability columns
  Array.from(present).filter((k) => k.endsWith(SKILL_SUFFIX)).forEach(push);
  // remaining (education etc.), keep Error + datetime last
  const enders = ["Error", "Analysis Datetime"];
  Array.from(present)
    .filter((k) => !seen.has(k) && !enders.includes(k))
    .forEach(push);
  enders.forEach(push);

  return ordered;
}

function num(v: unknown): number {
  const n = typeof v === "number" ? v : parseFloat(String(v));
  return Number.isFinite(n) ? n : 0;
}

export function applyFilters(rows: Row[], f: FilterState): Row[] {
  let out = rows;

  if (f.priorityBands.length) {
    out = out.filter((r) => f.priorityBands.includes(String(r["Priority Band"] ?? "")));
  }
  const search = f.search.trim().toLowerCase();
  if (search) {
    const fields = ["Skills", "Overall Remarks", "Internal Project Title", "External Project Title", "Full Name"];
    out = out.filter((r) => fields.some((fld) => String(r[fld] ?? "").toLowerCase().includes(search)));
  }
  const ranges: [string, [number, number]][] = [
    ["Overall Probability", f.overall],
    ["Skills Probability", f.skills],
    ["Experience Probability", f.experience],
    ["Projects Probability", f.projects],
    ["Other Probability", f.other],
  ];
  for (const [col, [lo, hi]] of ranges) {
    out = out.filter((r) => {
      const v = num(r[col]);
      return v >= lo && v <= hi;
    });
  }
  if (f.minTotalProjects) out = out.filter((r) => num(r["Total Projects Count"]) >= f.minTotalProjects);
  if (f.minInternalProjects) out = out.filter((r) => num(r["Internal Projects Count"]) >= f.minInternalProjects);
  if (f.minExternalProjects) out = out.filter((r) => num(r["External Projects Count"]) >= f.minExternalProjects);
  if (f.onlyInternal) out = out.filter((r) => num(r["Internal Projects Count"]) > 0);
  if (f.onlyExternal) out = out.filter((r) => num(r["External Projects Count"]) > 0);

  return out;
}

export function isShortlistingResult(rows: Row[]): boolean {
  return rows.some((r) => "Priority Band" in r || "Overall Probability" in r);
}
