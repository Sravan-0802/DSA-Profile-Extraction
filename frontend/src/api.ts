import type { AppConfig, JobStatus } from "./types";

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

export function buildDownloadUrl(jobId: string): string {
  return `${BASE}/jobs/${jobId}/download`;
}
