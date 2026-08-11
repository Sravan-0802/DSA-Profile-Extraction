import type { AppConfig, FilterState, JobStatus } from "./types";

const BASE = "/api";

export async function getConfig(): Promise<AppConfig> {
  const res = await fetch(`${BASE}/config`);
  if (!res.ok) throw new Error("Failed to load config");
  return res.json();
}

export interface CreateJobInput {
  mode: "shortlisting" | "extraction" | "dsa" | "github";
  analysisType: string;
  shortlistingMode: string;
  userRequirements: string;
  githubSkills: string;
  companyName: string;
  concurrency: number;
  inputMethod: "text" | "csv";
  pastedText: string;
  csvFile: File | null;
}

export async function createJob(input: CreateJobInput): Promise<{ job_id: string; total_rows: number }> {
  const fd = new FormData();
  fd.append("mode", input.mode);
  fd.append("analysis_type", input.analysisType);
  fd.append("shortlisting_mode", input.shortlistingMode);
  fd.append("user_requirements", input.userRequirements);
  fd.append("github_skills", input.githubSkills);
  fd.append("company_name", input.companyName);
  fd.append("concurrency", String(input.concurrency));
  fd.append("input_method", input.inputMethod);
  fd.append("pasted_text", input.pastedText);
  if (input.csvFile) fd.append("csv_file", input.csvFile);

  const res = await fetch(`${BASE}/jobs`, { method: "POST", body: fd });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || "Failed to create job");
  }
  return res.json();
}

export async function getJob(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${BASE}/jobs/${jobId}`);
  if (!res.ok) throw new Error("Failed to fetch job");
  return res.json();
}

export function buildDownloadUrl(jobId: string, filters: FilterState): string {
  const f = {
    priority_bands: filters.priorityBands,
    search: filters.search,
    overall_min: filters.overall[0],
    overall_max: filters.overall[1],
    skills_min: filters.skills[0],
    skills_max: filters.skills[1],
    experience_min: filters.experience[0],
    experience_max: filters.experience[1],
    projects_min: filters.projects[0],
    projects_max: filters.projects[1],
    other_min: filters.other[0],
    other_max: filters.other[1],
    min_total_projects: filters.minTotalProjects,
    min_internal_projects: filters.minInternalProjects,
    min_external_projects: filters.minExternalProjects,
    only_internal: filters.onlyInternal,
    only_external: filters.onlyExternal,
  };
  return `${BASE}/jobs/${jobId}/download?filters=${encodeURIComponent(JSON.stringify(f))}`;
}
