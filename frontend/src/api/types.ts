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

export interface CoverPlaylist {
  id: string;
  name: string;
  path: string | null;
  file_backed: boolean;
  has_sidecar: boolean;
}

export interface CoverStyle {
  id: string;
  label: string;
  prompt: string;
}

export interface CoverLayout {
  id: string;
  label: string;
  description: string;
  default_font: string;
}

export interface CoverFont {
  id: string;
  label: string;
  vibe: string;
}

export interface CoverBackground {
  id: string;
  source: "builtin" | "custom";
  name: string;
}

export interface CoverHistoryEntry {
  id: string;
  created: number;
  mode: "template" | "ai";
  filename: string;
  layout: string;
  font: string;
  background_id?: string;
  style?: string;
  prompt?: string;
}

export interface StudioTrack {
  id: string;
  title: string;
  artist: string;
}

export interface StudioEntry {
  id: string;
  created: number;
  kind: "instant" | "alchemy" | "refine";
  tracks: StudioTrack[];
  prompt?: string;
  instruction?: string;
  anchors?: StudioTrack[];
  excludes?: StudioTrack[];
  content_filter?: ContentFilter;
  filtered_out?: StudioTrack[];
  short?: boolean;
}

export interface StudioDiff {
  added: StudioTrack[];
  removed: StudioTrack[];
  kept: StudioTrack[];
  moved: StudioTrack[];
  filtered_out?: StudioTrack[];
}

export type ContentFilter = "any" | "christian" | "worship" | "no_christian";

export interface ArtistRow {
  artist: string;
  genre: string;
  worship: string; // "yes" | "no" | "unknown"
  tier: string;
  ambiguous: string; // "yes" | "no"
  enabled: string; // "yes" | "no"
  mbid: string;
  notes: string;
  [key: string]: string;
}

export interface ChristianSettings {
  prune: boolean;
}

export interface ScanDecisionRow {
  name: string;
  albums: string[];
  mbid_suggestion: string | null;
  count: number;
}

export interface ScanSuggestionRow {
  name: string;
  genres: string[];
  count: number;
}

export interface ScanResult {
  needs_decision: ScanDecisionRow[];
  suggestions: ScanSuggestionRow[];
  not_in_library: string[];
  library_counts: Record<string, number>;
}

export interface SeedDiff {
  new_count: number;
  sample: string[];
}

export interface MigrationLog {
  changed: boolean;
  migrated_at: number;
  worship_enabled: string[];
  disabled: string[];
}
