// Shared shapes for the Duplicate Finder page and its sub-components,
// mirroring app/modules/duplicate_finder/service.py's scan payload exactly
// (including props/tags, which the backend has always sent but which went
// undeclared - and therefore unused - in the original port of this page).

export interface Edition {
  folder: string;
  artist: string;
  album: string;
  year: string;
  format: string;
  detail: string;
  tier: string;
  tracks: number;
  keep: boolean;
}

export interface FileEntry {
  rel: string;
  name: string;
  ed: number;
  format: string;
  detail: string;
  tier: string;
  secs: number;
  size: number;
  mtime: number;
  source: string;
  source_why: string;
  quality: "best" | "lower";
  stray: boolean;
  fit: { tone: string; text: string };
  keep_pref: boolean;
  keep_why: string;
  upgrade: { replace: string; to: string; replaces: string; folder: string; name: string } | null;
  suggested: boolean;
  moved: boolean;
  props: Record<string, string>;
  tags: Record<string, string>;
}

export interface Row {
  title: string;
  track: number | null;
  disc: number;
  evidence: { tone: string; text: string; why: string }[];
  fingerprint: string;
  files: FileEntry[];
}

export interface Cluster {
  key: string;
  kind: "suggested" | "manual" | "other";
  reason: string;
  detail: string;
  ignored: boolean;
  editions: Edition[];
  rows: Row[];
  artist: string;
  album: string;
}

export interface ScanState {
  status: "idle" | "scanning" | "done" | "error";
  phase: string;
  scanned: number;
  total: number;
  unreadable: number;
  skip_fp: boolean;
  warnings: string[];
  clusters: Cluster[];
  error: string | null;
}

export interface QuarantineBatch {
  batch: string;
  created: number;
  files: { rel: string; size: number; quality: string }[];
  moves: { from: string; to: string }[];
  bytes: number;
}
