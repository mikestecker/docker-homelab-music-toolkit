import { Fragment } from "react";
import DiffText from "./DiffText";
import type { Cluster, FileEntry, Row } from "./types";

function kindChipClass(kind: Cluster["kind"]) {
  return kind === "suggested" ? "good" : kind === "other" ? "warn" : "bad";
}

export default function ClusterCard({
  cluster: c,
  open,
  onToggleOpen,
  selected,
  onToggleFile,
  onSelectRemovable,
  onKeepBoth,
  onUpgrade,
  onPreview,
  nowPlaying,
  onCompareTags,
  showIgnoreControls,
}: {
  cluster: Cluster;
  open: boolean;
  onToggleOpen: () => void;
  selected: Set<string>;
  onToggleFile: (file: FileEntry, row: Row) => void;
  onSelectRemovable: (c: Cluster) => void;
  onKeepBoth: (key: string, kept: boolean) => void;
  onUpgrade: (rel: string) => void;
  onPreview: (rel: string) => void;
  nowPlaying: string | null;
  onCompareTags: (row: Row) => void;
  showIgnoreControls: boolean;
}) {
  const selectedHere = c.rows.flatMap((r) => r.files).filter((f) => selected.has(f.rel)).length;
  const editionRef = c.editions[0]?.folder.split("/").slice(1).join("/") || c.editions[0]?.folder;

  return (
    <div className="panel">
      <div className="row">
        <button onClick={onToggleOpen} title={open ? "Collapse" : "Expand"} style={{ fontFamily: "monospace" }}>
          {open ? "▾" : "▸"}
        </button>
        <strong>
          {c.artist} — {c.album}
        </strong>
        <span className={`chip ${kindChipClass(c.kind)}`}>{c.reason}</span>
        <span className="muted">
          {c.rows.length} track{c.rows.length === 1 ? "" : "s"}
          {selectedHere > 0 && `, ${selectedHere} selected`}
        </span>
        <div style={{ marginLeft: "auto" }} />
        {!showIgnoreControls && (
          <>
            <button onClick={() => onSelectRemovable(c)}>Select all removable</button>
            <button onClick={() => onKeepBoth(c.key, true)}>Keep both / ignore</button>
          </>
        )}
        {showIgnoreControls && <button onClick={() => onKeepBoth(c.key, false)}>Show again</button>}
      </div>
      <p className="muted">{c.detail}</p>

      {open && (
        <>
          <div style={{ overflowX: "auto" }}>
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
                      <tr key={f.rel} style={nowPlaying === f.rel ? { background: "var(--border)" } : undefined}>
                        <td>
                          {!f.moved && (
                            <input
                              type="checkbox"
                              checked={selected.has(f.rel)}
                              onChange={() => onToggleFile(f, r)}
                            />
                          )}
                          {f.moved && <span className="chip good">moved</span>}
                        </td>
                        {fi === 0 && <td rowSpan={r.files.length}>{r.title}</td>}
                        {fi !== 0 && <td style={{ display: "none" }} />}
                        <td>
                          <button onClick={() => onPreview(f.rel)} style={{ fontSize: 12, padding: "2px 8px" }}>
                            {nowPlaying === f.rel ? "⏸" : "▶"}
                          </button>{" "}
                          <DiffText value={f.name} reference={r.files.length > 1 ? r.files[0].name : undefined} />
                          {f.suggested && (
                            <span className="chip warn" style={{ marginLeft: 6 }}>
                              suggested
                            </span>
                          )}
                          {" "}
                          <button onClick={() => onCompareTags(r)} style={{ fontSize: 12, padding: "2px 8px" }}>
                            Compare
                          </button>
                        </td>
                        <td>
                          {(() => {
                            const folder = c.editions[f.ed]?.folder.split("/").slice(1).join("/") || c.editions[f.ed]?.folder || "";
                            return <DiffText value={folder} reference={c.editions.length > 1 ? editionRef : undefined} />;
                          })()}
                        </td>
                        <td>
                          {f.format} {f.detail} <span className="muted">({f.quality})</span>
                        </td>
                        <td className="muted" title={f.source_why || undefined}>
                          {f.source}
                        </td>
                        <td>
                          {f.fit.text && <span className={`chip ${f.fit.tone || "warn"}`}>{f.fit.text}</span>}
                          {f.keep_why && <div className="muted">kept: {f.keep_why}</div>}
                        </td>
                        <td>
                          {f.upgrade && <button onClick={() => onUpgrade(f.rel)}>Upgrade {f.upgrade.replaces}</button>}
                        </td>
                      </tr>
                    ))}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
          {evidenceRow(c)}
        </>
      )}
    </div>
  );
}

function evidenceRow(c: Cluster) {
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
