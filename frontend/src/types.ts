export type Row = Record<string, unknown>;

export interface AppConfig {
  has_ai: boolean;
  mistral_key_count: number;
  mistral_model: string;
  has_github: boolean;
  github_token_count: number;
  ocr_available: boolean;
  default_concurrency: number;
  max_concurrency: number;
  analysis_types: string[];
  shortlisting_modes: string[];
}

export interface JobPayload {
  mode: string;
  analysis_type: string;
  shortlisting_mode: string;
  user_requirements: string;
  github_skills: string;
  company_name: string;
  concurrency: number;
}

export interface JobStatus {
  id: string;
  status: "queued" | "running" | "completed" | "failed";
  total: number;
  completed: number;
  progress: number;
  payload: JobPayload;
  warnings: string[];
  errors: string[];
  started_at?: string;
  finished_at?: string;
  live_results: Row[];
  results: Row[];
  file_name: string;
}

export interface FilterState {
  priorityBands: string[];
  search: string;
  overall: [number, number];
  skills: [number, number];
  experience: [number, number];
  projects: [number, number];
  other: [number, number];
  minTotalProjects: number;
  minInternalProjects: number;
  minExternalProjects: number;
  onlyInternal: boolean;
  onlyExternal: boolean;
}

export const defaultFilters: FilterState = {
  priorityBands: [],
  search: "",
  overall: [0, 100],
  skills: [0, 100],
  experience: [0, 100],
  projects: [0, 100],
  other: [0, 100],
  minTotalProjects: 0,
  minInternalProjects: 0,
  minExternalProjects: 0,
  onlyInternal: false,
  onlyExternal: false,
};
