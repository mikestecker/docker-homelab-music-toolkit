import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import ClusterCard from "../components/duplicate-finder/ClusterCard";
import TagCompareDrawer from "../components/duplicate-finder/TagCompareDrawer";
import type { Cluster, FileEntry, QuarantineBatch, Row, ScanState } from "../components/duplicate-finder/types";
import ErrorBanner from "../components/ErrorBanner";
import Toast from "../components/Toast";
import { useApiError } from "../hooks/useApiError";
import { useToast } from "../hooks/useToast";

type Tab = "suggested" | "manual" | "other" | "kept";

const TAB_LABEL: Record<Tab, string> = {
  suggested: "Suggested",
  manual: "Review",
  other: "Other albums",
  kept: "Kept both",
};

const SECTION_HELP: Record<Tab, string> = {
  suggested: "The app is confident. Redundant copies are already selected below — look it over, then quarantine.",
  manual: "These need your ears. Nothing is pre-selected — compare tags, preview audio, then select what to remove or Keep both.",
  other: "The same recording on a different release (an album, a single, a best-of). Both stay; nothing is selected.",
  kept: "Albums you've told the app to leave alone. If a new copy shows up later, it comes back for review.",
};

function fmtBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

function fmtDate(epochSeconds: number) {
  return new Date(epochSeconds * 1000).toLocaleString();
}

export default function DuplicateFinderPage() {
  const { error, run } = useApiError();
  const toast = useToast();
  const [scan, setScan] = useState<ScanState | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [quarantine, setQuarantine] = useState<QuarantineBatch[]>([]);
  const [preview, setPreview] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("suggested");
  const [query, setQuery] = useState("");
  const [reasonFilter, setReasonFilter] = useState("");
  const [closedCards, setClosedCards] = useState<Set<string>>(new Set());
  const [compareRow, setCompareRow] = useState<Row | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

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

  // / focuses search, Escape closes the player - suppressed while typing.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (document.activeElement?.tagName || "").toLowerCase();
      const typing = tag === "input" || tag === "textarea" || tag === "select";
      if (e.key === "/" && !typing) {
        e.preventDefault();
        searchRef.current?.focus();
      } else if (e.key === "Escape" && preview) {
        setPreview(null);
      } else if ((e.key === "b" || e.key === "B") && !typing && preview) {
        switchCopy();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preview]);

  const startScan = () => {
    run(() => api.post("/api/dupes/scan")).then(() => {
      setSelected(new Set());
      pollRef.current = setInterval(loadScanState, 700);
    });
  };

  const skipFingerprints = () => run(() => api.post("/api/dupes/scan/skip-fingerprints")).then(() => loadScanState());

  const toggleFile = (f: FileEntry, row: Row) => {
    setSelected((prev) => {
      if (prev.has(f.rel)) {
        const next = new Set(prev);
        next.delete(f.rel);
        return next;
      }
      const live = row.files.filter((x) => !x.moved);
      const stillUnselected = live.filter((x) => x.rel !== f.rel && !prev.has(x.rel));
      if (live.length > 0 && stillUnselected.length === 0) {
        toast.show({ tone: "warn", message: "Leave at least one copy of every track." });
        return prev;
      }
      const next = new Set(prev);
      next.add(f.rel);
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
    run(() =>
      api.post<{ batch: string | null; moved: number; bytes: number; errors: string[] }>("/api/dupes/quarantine", {
        paths,
      }),
    ).then((r) => {
      if (!r) return;
      setSelected(new Set());
      loadScanState();
      loadQuarantine();
      if (r.moved > 0) {
        toast.show({
          tone: "good",
          message: `Quarantined ${r.moved} file${r.moved === 1 ? "" : "s"}, ${fmtBytes(r.bytes)}.`,
          detail: r.errors.length ? r.errors : undefined,
          action: r.batch ? { label: "Undo", onClick: () => void restore(r.batch as string) } : undefined,
        });
      } else {
        toast.show({ tone: "bad", message: "Nothing was quarantined.", detail: r.errors });
      }
    });
  };

  const keepBoth = (key: string, kept: boolean) =>
    run(() => api.post("/api/dupes/keep-both", { key, kept })).then(() => loadScanState());

  const upgrade = (rel: string) => run(() => api.post("/api/dupes/upgrade", { rel })).then(() => loadScanState());

  const restore = (batch: string) =>
    run(() => api.post<{ restored: number; errors: string[] }>("/api/dupes/restore", { batch })).then((r) => {
      loadScanState();
      loadQuarantine();
      if (r) toast.show({ tone: "good", message: `Restored ${r.restored} file${r.restored === 1 ? "" : "s"}.` });
    });

  const purge = (batch: string) => {
    if (!confirm(`Permanently delete everything in batch ${batch}? This can't be undone.`)) return;
    run(() => api.post("/api/dupes/purge", { batch })).then(() => loadQuarantine());
  };

  const allClusters = scan?.clusters ?? [];
  const counts = useMemo(
    () => ({
      suggested: allClusters.filter((c) => !c.ignored && c.kind === "suggested").length,
      manual: allClusters.filter((c) => !c.ignored && c.kind === "manual").length,
      other: allClusters.filter((c) => !c.ignored && c.kind === "other").length,
      kept: allClusters.filter((c) => c.ignored).length,
    }),
    [allClusters],
  );

  const tabClusters = useMemo(() => {
    if (tab === "kept") return allClusters.filter((c) => c.ignored);
    const notIgnored = allClusters.filter((c) => !c.ignored);
    return notIgnored.filter((c) => c.kind === tab);
  }, [allClusters, tab]);

  const reasons = useMemo(() => Array.from(new Set(tabClusters.map((c) => c.reason))).sort(), [tabClusters]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return tabClusters.filter((c) => {
      if (reasonFilter && c.reason !== reasonFilter) return false;
      if (!q) return true;
      if (c.artist.toLowerCase().includes(q) || c.album.toLowerCase().includes(q)) return true;
      if (c.editions.some((e) => e.folder.toLowerCase().includes(q))) return true;
      return c.rows.some((r) => r.title.toLowerCase().includes(q));
    });
  }, [tabClusters, query, reasonFilter]);

  const findRowForFile = (rel: string): Row | null => {
    for (const c of allClusters) for (const r of c.rows) if (r.files.some((f) => f.rel === rel)) return r;
    return null;
  };

  const switchCopy = () => {
    if (!preview) return;
    const row = findRowForFile(preview);
    if (!row) return;
    const other = row.files.find((f) => f.rel !== preview && !f.moved);
    if (!other) return;
    const t = audioRef.current?.currentTime ?? 0;
    setPreview(other.rel);
    requestAnimationFrame(() => {
      if (audioRef.current) audioRef.current.currentTime = t;
    });
  };

  return (
    <div style={{ paddingBottom: preview || toast.toast ? 90 : 0 }}>
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
          {scan?.status === "scanning" && scan.phase === "Fingerprinting" && !scan.skip_fp && (
            <button onClick={skipFingerprints}>Skip fingerprinting</button>
          )}
          {scan?.status === "done" && (
            <span className="muted">
              Scanned {scan.scanned} files, {allClusters.filter((c) => !c.ignored).length} duplicate clusters,{" "}
              {scan.unreadable} unreadable
            </span>
          )}
          {scan?.status === "error" && <span className="chip bad">{scan.error}</span>}
        </div>
      </div>

      {scan && scan.status !== "idle" && (
        <>
          <div className="panel sticky-toolbar">
            <div className="row">
              {(Object.keys(TAB_LABEL) as Tab[]).map((t) => (
                <button key={t} className={tab === t ? "primary" : ""} onClick={() => setTab(t)}>
                  {TAB_LABEL[t]} ({counts[t]})
                </button>
              ))}
              <input
                ref={searchRef}
                type="text"
                placeholder="Filter by artist, album or track (press /)"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                style={{ marginLeft: "auto", minWidth: 220 }}
              />
              <select value={reasonFilter} onChange={(e) => setReasonFilter(e.target.value)}>
                <option value="">Any reason</option>
                {reasons.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
              <button onClick={() => setClosedCards(new Set())}>Expand all</button>
              <button onClick={() => setClosedCards(new Set(allClusters.map((c) => c.key)))}>Collapse all</button>
            </div>
            <p className="muted" style={{ marginBottom: 0 }}>
              {SECTION_HELP[tab]}
            </p>
            {selected.size > 0 && (
              <div className="row" style={{ marginTop: 10, marginBottom: 0 }}>
                <span>{selected.size} selected</span>
                <button className="primary" onClick={quarantineSelected}>
                  Quarantine selected
                </button>
                <button onClick={() => setSelected(new Set())}>Clear selection</button>
              </div>
            )}
          </div>

          {filtered.length === 0 && <p className="muted">Nothing here.</p>}
          {filtered.map((c) => (
            <ClusterCard
              key={c.key}
              cluster={c}
              open={!closedCards.has(c.key)}
              onToggleOpen={() =>
                setClosedCards((prev) => {
                  const next = new Set(prev);
                  next.has(c.key) ? next.delete(c.key) : next.add(c.key);
                  return next;
                })
              }
              selected={selected}
              onToggleFile={toggleFile}
              onSelectRemovable={selectRemovable}
              onKeepBoth={keepBoth}
              onUpgrade={upgrade}
              onPreview={setPreview}
              nowPlaying={preview}
              onCompareTags={setCompareRow}
              showIgnoreControls={tab === "kept"}
            />
          ))}
        </>
      )}

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Quarantine</h3>
        {quarantine.length === 0 && <p className="muted">Nothing quarantined.</p>}
        {quarantine.map((b) => (
          <div key={b.batch} className="row">
            <span>{b.batch}</span>
            <span className="muted">
              {b.files.length} files, {fmtBytes(b.bytes)} — {fmtDate(b.created)}
            </span>
            <button onClick={() => restore(b.batch)}>Restore</button>
            <button onClick={() => purge(b.batch)}>Delete permanently</button>
          </div>
        ))}
      </div>

      <TagCompareDrawer open={!!compareRow} onClose={() => setCompareRow(null)} row={compareRow} />

      {(preview || toast.toast) && (
        <div className="dock">
          <Toast toast={toast.toast} onDismiss={toast.dismiss} />
          {preview && (
            <div className="player-bar">
              <span className="muted" style={{ marginRight: 10 }}>
                {preview}
              </span>
              <audio
                ref={audioRef}
                controls
                autoPlay
                style={{ flex: 1, minWidth: 0 }}
                src={`/api/dupes/audio?rel=${encodeURIComponent(preview || "")}`}
              />
              <button onClick={switchCopy} title="Switch to the other copy at the same point (B)">
                Switch copy <kbd>B</kbd>
              </button>
              <button onClick={() => setPreview(null)}>Close</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
