import { Fragment, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import ErrorBanner from "../components/ErrorBanner";
import { useApiError } from "../hooks/useApiError";

interface Edition {
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

interface FileEntry {
  rel: string;
  name: string;
  ed: number;
  format: string;
  detail: string;
  tier: string;
  secs: number;
  size: number;
  source: string;
  quality: "best" | "lower";
  stray: boolean;
  fit: { tone: string; text: string };
  keep_pref: boolean;
  keep_why: string;
  upgrade: { replace: string; to: string; replaces: string; folder: string; name: string } | null;
  suggested: boolean;
  moved: boolean;
}

interface Row {
  title: string;
  track: number | null;
  disc: number;
  evidence: { tone: string; text: string; why: string }[];
  fingerprint: string;
  files: FileEntry[];
}

interface Cluster {
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

interface ScanState {
  status: "idle" | "scanning" | "done" | "error";
  phase: string;
  scanned: number;
  total: number;
  unreadable: number;
  warnings: string[];
  clusters: Cluster[];
  error: string | null;
}

interface QuarantineBatch {
  batch: string;
  created: number;
  files: { rel: string; size: number; quality: string }[];
  moves: { from: string; to: string }[];
  bytes: number;
}

function fmtBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export default function DuplicateFinderPage() {
  const { error, run } = useApiError();
  const [scan, setScan] = useState<ScanState | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [quarantine, setQuarantine] = useState<QuarantineBatch[]>([]);
  const [preview, setPreview] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadScanState = () =>
    run(() => api.get<ScanState>("/api/dupes/scan")).then((s) => {
      if (!s) return;
      setScan(s);
      if (s.status !== "scanning" && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    });

  const loadQuarantine = () =>
    run(() => api.get<QuarantineBatch[]>("/api/dupes/quarantine")).then((q) => q && setQuarantine(q));

  useEffect(() => {
    loadScanState();
    loadQuarantine();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startScan = () => {
    run(() => api.post("/api/dupes/scan")).then(() => {
      setSelected(new Set());
      pollRef.current = setInterval(loadScanState, 700);
    });
  };

  const toggle = (rel: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(rel) ? next.delete(rel) : next.add(rel);
      return next;
    });
  };

  const selectRemovable = (c: Cluster) => {
    setSelected((prev) => {
      const next = new Set(prev);
      for (const r of c.rows) for (const f of r.files) if (!f.keep_pref && !f.moved) next.add(f.rel);
      return next;
    });
  };

  const quarantineSelected = () => {
    const paths = Array.from(selected);
    if (paths.length === 0) return;
    run(() => api.post<{ moved: number; errors: string[] }>("/api/dupes/quarantine", { paths })).then((r) => {
      if (!r) return;
      setSelected(new Set());
      loadScanState();
      loadQuarantine();
      if (r.errors.length) alert(r.errors.join("\n"));
    });
  };

  const keepBoth = (key: string, kept: boolean) =>
    run(() => api.post("/api/dupes/keep-both", { key, kept })).then(() => loadScanState());

  const upgrade = (rel: string) => run(() => api.post("/api/dupes/upgrade", { rel })).then(() => loadScanState());

  const restore = (batch: string) =>
    run(() => api.post("/api/dupes/restore", { batch })).then(() => {
      loadScanState();
      loadQuarantine();
    });

  const purge = (batch: string) => {
    if (!confirm(`Permanently delete everything in batch ${batch}? This can't be undone.`)) return;
    run(() => api.post("/api/dupes/purge", { batch })).then(() => loadQuarantine());
  };

  const visibleClusters = (scan?.clusters ?? []).filter((c) => !c.ignored);

  return (
    <div>
      <h2>Duplicate finder</h2>
      <ErrorBanner message={error} />

      <div className="panel">
        <div className="row">
          <button className="primary" disabled={scan?.status === "scanning"} onClick={startScan}>
            {scan?.status === "scanning" ? "Scanning…" : "Scan library"}
          </button>
          {scan?.status === "scanning" && (
            <span className="muted">
              {scan.phase} ({scan.scanned}/{scan.total || "?"})
            </span>
          )}
          {scan?.status === "done" && (
            <span className="muted">
              Scanned {scan.scanned} files, {visibleClusters.length} duplicate clusters, {scan.unreadable} unreadable
            </span>
          )}
          {scan?.status === "error" && <span className="chip bad">{scan.error}</span>}
        </div>
        {selected.size > 0 && (
          <div className="row">
            <span>{selected.size} selected</span>
            <button className="primary" onClick={quarantineSelected}>
              Quarantine selected
            </button>
            <button onClick={() => setSelected(new Set())}>Clear selection</button>
          </div>
        )}
      </div>

      {visibleClusters.map((c) => (
        <div className="panel" key={c.key}>
          <div className="row">
            <strong>
              {c.artist} — {c.album}
            </strong>
            <span className={`chip ${c.kind === "suggested" ? "good" : c.kind === "other" ? "warn" : "bad"}`}>
              {c.reason}
            </span>
            <button style={{ marginLeft: "auto" }} onClick={() => selectRemovable(c)}>
              Select all removable
            </button>
            <button onClick={() => keepBoth(c.key, true)}>Keep both / ignore</button>
          </div>
          <p className="muted">{c.detail}</p>
          <table>
            <thead>
              <tr>
                <th></th>
                <th>Track</th>
                <th>File</th>
                <th>Edition</th>
                <th>Quality</th>
                <th>Source</th>
                <th>Fit</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {c.rows.map((r, ri) => (
                <Fragment key={`${r.disc}-${r.track}-${r.title}-${ri}`}>
                  {r.files.map((f, fi) => (
                    <tr key={f.rel}>
                      <td>
                        {!f.moved && (
                          <input type="checkbox" checked={selected.has(f.rel)} onChange={() => toggle(f.rel)} />
                        )}
                        {f.moved && <span className="chip good">moved</span>}
                      </td>
                      {fi === 0 && <td rowSpan={r.files.length}>{r.title}</td>}
                      {fi !== 0 && <td style={{ display: "none" }} />}
                      <td>
                        <button onClick={() => setPreview(f.rel)} style={{ fontSize: 12, padding: "2px 8px" }}>
                          ▶
                        </button>{" "}
                        {f.name}
                        {f.suggested && <span className="chip warn" style={{ marginLeft: 6 }}>suggested</span>}
                      </td>
                      <td>{c.editions[f.ed]?.folder.split("/").slice(1).join("/") || c.editions[f.ed]?.folder}</td>
                      <td>
                        {f.format} {f.detail} <span className="muted">({f.quality})</span>
                      </td>
                      <td className="muted">{f.source}</td>
                      <td>
                        {f.fit.text && <span className={`chip ${f.fit.tone || "warn"}`}>{f.fit.text}</span>}
                        {f.keep_why && <div className="muted">kept: {f.keep_why}</div>}
                      </td>
                      <td>
                        {f.upgrade && <button onClick={() => upgrade(f.rel)}>Upgrade {f.upgrade.replaces}</button>}
                      </td>
                    </tr>
                  ))}
                </Fragment>
              ))}
            </tbody>
          </table>
          {r_evidence(c)}
        </div>
      ))}

      {preview && (
        <div className="panel">
          <div className="row">
            <strong>{preview}</strong>
            <button onClick={() => setPreview(null)}>Close</button>
          </div>
          <audio controls style={{ width: "100%" }} src={`/api/dupes/audio?rel=${encodeURIComponent(preview)}`} />
        </div>
      )}

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Quarantine</h3>
        {quarantine.length === 0 && <p className="muted">Nothing quarantined.</p>}
        {quarantine.map((b) => (
          <div key={b.batch} className="row">
            <span>{b.batch}</span>
            <span className="muted">
              {b.files.length} files, {fmtBytes(b.bytes)}
            </span>
            <button onClick={() => restore(b.batch)}>Restore</button>
            <button onClick={() => purge(b.batch)}>Delete permanently</button>
          </div>
        ))}
      </div>
    </div>
  );
}

function r_evidence(c: Cluster) {
  const chips = c.rows.flatMap((r) => r.evidence);
  if (chips.length === 0) return null;
  return (
    <div className="row" style={{ marginTop: 8 }}>
      {chips.map((e, i) => (
        <span key={i} className={`chip ${e.tone === "good" ? "good" : e.tone === "warn" ? "warn" : "bad"}`} title={e.why}>
          {e.text}
        </span>
      ))}
    </div>
  );
}
