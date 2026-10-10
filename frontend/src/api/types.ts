// Loosely-typed mirrors of the backend's structured preview/apply results.
// Every module returns the same {dry_run, log, ...} shape, so RunResult
// covers the common fields and each module's own extra fields are left as
// index access rather than exhaustively modeled.

export interface RunResult {
  dry_run?: boolean;
  log: string[];
  error: string | null;
  [key: string]: unknown;
}

export interface JobInfo {
  id: string;
  label: string;
  enabled: boolean;
  hour: number | null;
  minute: number | null;
  next_run: string | null;
  last_run: RunRecord | null;
}

export interface RunRecord {
  id: string;
  job_id: string;
  trigger: "manual" | "scheduled";
  started: number;
  finished: number | null;
  status: "running" | "ok" | "error";
  result: RunResult | null;
  error: string | null;
}

export interface StatusResponse {
  navidrome: {
    reachable: boolean;
    version: string | null;
    server_version: string | null;
    playlist_count: number | null;
    error: string | null;
  };
  audiomuse: { reachable: boolean };
  jobs: JobInfo[];
}

export interface SeedPrompt {
  name: string;
  n?: number;
  concept?: string;
  faith?: boolean;
  top?: string[];
  prompt: string;
  journey?: string;
  alchemy?: string[];
  [key: string]: unknown;
}

export interface Recipe {
  name: string;
  size?: number;
  cap?: number;
  artists?: string[];
  staples?: string[];
  prompt: string;
  [key: string]: unknown;
}
