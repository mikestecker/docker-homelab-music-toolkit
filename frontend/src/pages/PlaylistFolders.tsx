import { useEffect, useState } from "react";
import { api } from "../api/client";
import ErrorBanner from "../components/ErrorBanner";
import LogPanel from "../components/LogPanel";
import { useApiError } from "../hooks/useApiError";

interface PlaylistEntry {
  id: string;
  name: string;
  owner: string | null;
}

interface CurrentResponse {
  folders: Record<string, PlaylistEntry[]>;
  error: string | null;
}

interface Item {
  id: string;
  name: string;
  new_name: string;
  owner: string | null;
  not_owned: boolean;
  fail: string | null;
}

interface RunResult {
  dry_run: boolean;
  log: string[];
  items: Item[];
  changed_count: number;
  error: string | null;
}

export default function PlaylistFoldersPage() {
  const { error, run } = useApiError();
  const [current, setCurrent] = useState<CurrentResponse | null>(null);
  const [mapText, setMapText] = useState("");
  const [result, setResult] = useState<RunResult | null>(null);
  const [assignFrom, setAssignFrom] = useState("");
  const [assignTo, setAssignTo] = useState("");
  const [busy, setBusy] = useState(false);

  const loadCurrent = () => run(() => api.get<CurrentResponse>("/api/playlist-folders/current")).then((r) => r && setCurrent(r));

  useEffect(() => {
    loadCurrent();
    run(() => api.get<{ text: string }>("/api/playlist-folders/map")).then((r) => r && setMapText(r.text));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const saveMap = () => run(() => api.put("/api/playlist-folders/map", { text: mapText }));

  const assign = () => {
    if (!assignFrom || !assignTo) return;
    run(() => api.post("/api/playlist-folders/assign", { old_name: assignFrom, new_full_name: assignTo })).then(() => {
      setAssignFrom("");
      setAssignTo("");
      run(() => api.get<{ text: string }>("/api/playlist-folders/map")).then((r) => r && setMapText(r.text));
    });
  };

  const doRun = (apply: boolean) => {
    setBusy(true);
    run(() => api.post<RunResult>(`/api/playlist-folders/${apply ? "apply" : "preview"}`))
      .then((r) => {
        if (r) setResult(r);
        if (apply) loadCurrent();
      })
      .finally(() => setBusy(false));
  };

  return (
    <div>
      <h2>Playlist folders</h2>
      <p className="muted">
        Files playlists into folders by renaming them (<code>Folder/Subfolder/Name</code>). The map below is the
        source of truth; assigning a folder here writes a rule into it.
      </p>
      <ErrorBanner message={error} />

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Current playlists, by folder</h3>
        {current &&
          Object.entries(current.folders).map(([folder, playlists]) => (
            <div key={folder} style={{ marginBottom: 10 }}>
              <strong>{folder || "(ungrouped)"}</strong>
              <ul style={{ margin: "4px 0 0 18px" }}>
                {playlists.map((p) => (
                  <li key={p.id}>{p.name}</li>
                ))}
              </ul>
            </div>
          ))}
        <div className="row" style={{ marginTop: 10 }}>
          <input
            type="text"
            placeholder="Playlist name"
            value={assignFrom}
            onChange={(e) => setAssignFrom(e.target.value)}
          />
          <span>→</span>
          <input
            type="text"
            placeholder="Folder/Subfolder/Name"
            value={assignTo}
            onChange={(e) => setAssignTo(e.target.value)}
          />
          <button onClick={assign}>Assign</button>
        </div>
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Map file</h3>
        <textarea rows={14} value={mapText} onChange={(e) => setMapText(e.target.value)} />
        <div className="row" style={{ marginTop: 10 }}>
          <button onClick={saveMap}>Save map</button>
        </div>
      </div>

      <div className="panel">
        <div className="row">
          <button disabled={busy} onClick={() => doRun(false)}>
            Preview
          </button>
          <button className="primary" disabled={busy} onClick={() => doRun(true)}>
            Apply
          </button>
          {result && <span className="muted">Changed: {result.changed_count}</span>}
        </div>
        {result && result.items.length > 0 && (
          <table style={{ marginTop: 10 }}>
            <thead>
              <tr>
                <th>Name</th>
                <th>New name</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {result.items.map((i) => (
                <tr key={i.id}>
                  <td>{i.name}</td>
                  <td>{i.new_name}</td>
                  <td>
                    {i.not_owned && <span className="chip warn">not owned</span>}
                    {i.fail && <span className="chip bad">{i.fail}</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <LogPanel lines={result?.log} />
      </div>
    </div>
  );
}
