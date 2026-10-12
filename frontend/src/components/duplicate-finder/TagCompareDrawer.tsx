import { useState } from "react";
import Drawer from "../Drawer";
import type { Row } from "./types";

// A fixed, always-shown set of technical properties (small and stable, never
// noisy) plus an optional union of every raw tag found on any copy (can be
// large/noisy, so collapsed behind "Show all tags" by default - mirrors
// docker-music-dupes' own "show matching fields" toggle for the same reason).

function buildRows(keys: string[], files: Row["files"], pick: (f: Row["files"][number]) => Record<string, string>) {
  return keys.map((key) => {
    const values = files.map((f) => pick(f)[key] ?? "");
    const differs = new Set(values.filter((v) => v)).size > 1;
    return { key, values, differs };
  });
}

export default function TagCompareDrawer({ open, onClose, row }: { open: boolean; onClose: () => void; row: Row | null }) {
  const [showAllTags, setShowAllTags] = useState(false);

  if (!row) return null;
  const files = row.files;

  const propKeys = Array.from(new Set(files.flatMap((f) => Object.keys(f.props))));
  const propRows = buildRows(propKeys, files, (f) => f.props);

  const tagKeys = Array.from(new Set(files.flatMap((f) => Object.keys(f.tags)))).sort();
  const allTagRows = buildRows(tagKeys, files, (f) => f.tags);
  const tagRows = showAllTags ? allTagRows : allTagRows.filter((r) => r.differs);

  return (
    <Drawer open={open} onClose={onClose}>
      <div className="row" style={{ justifyContent: "space-between", flexWrap: "nowrap" }}>
        <h3 style={{ marginTop: 0 }}>{row.title}</h3>
        <button onClick={onClose}>✕</button>
      </div>
      <p className="muted">Comparing {files.length} {files.length === 1 ? "copy" : "copies"}.</p>

      <h4>Properties</h4>
      <div style={{ overflowX: "auto" }}>
        <table>
          <thead>
            <tr>
              <th>Field</th>
              {files.map((f) => (
                <th key={f.rel}>{f.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {propRows.map((r) => (
              <tr key={r.key}>
                <td className="muted">{r.key}</td>
                {r.values.map((v, i) => (
                  <td key={i} className={r.differs ? "differs" : undefined}>
                    {v ? v : <em className="muted">missing</em>}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="row" style={{ marginTop: 16 }}>
        <h4 style={{ margin: 0 }}>Tags</h4>
        <label style={{ flexDirection: "row", alignItems: "center", gap: 6, marginLeft: "auto" }}>
          <input type="checkbox" checked={showAllTags} onChange={(e) => setShowAllTags(e.target.checked)} />
          Show all tags, not just the ones that differ
        </label>
      </div>
      {tagRows.length === 0 && <p className="muted">{showAllTags ? "No tags found." : "Every tag matches."}</p>}
      {tagRows.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>Tag</th>
                {files.map((f) => (
                  <th key={f.rel}>{f.name}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tagRows.map((r) => (
                <tr key={r.key}>
                  <td className="muted">{r.key}</td>
                  {r.values.map((v, i) => (
                    <td key={i} className={r.differs ? "differs" : undefined}>
                      {v ? v : <em className="muted">missing</em>}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Drawer>
  );
}
