import { useEffect, useState } from "react";
import { api } from "../api/client";
import ErrorBanner from "../components/ErrorBanner";
import LogPanel from "../components/LogPanel";
import { useApiError } from "../hooks/useApiError";

interface Settings {
  prefix: string;
  path_match: string;
}

interface Item {
  id: string;
  name: string;
  new_name: string;
  fail: string | null;
}

interface RunResult {
  dry_run: boolean;
  undo: boolean;
  log: string[];
  items: Item[];
  changed_count: number;
  error: string | null;
}

export default function TidarrImportsPage() {
  const { error, run } = useApiError();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [result, setResult] = useState<RunResult | null>(null);
  const [undo, setUndo] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    run(() => api.get<Settings>("/api/tidarr-tagging/settings")).then((r) => r && setSettings(r));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const saveSettings = () =>
    settings &&
    run(() => api.put<Settings>("/api/tidarr-tagging/settings", settings)).then((r) => r && setSettings(r));

  const doRun = (apply: boolean) => {
    setBusy(true);
    run(() => api.post<RunResult>(`/api/tidarr-tagging/${apply ? "apply" : "preview"}`, { undo }))
      .then((r) => r && setResult(r))
      .finally(() => setBusy(false));
  };

  return (
    <div>
      <h2>Tidarr import filing</h2>
      <p className="muted">
        Prefixes and tags playlists Navidrome imported from Tidarr's <code>.m3u</code> files, so they group together
        in every client.
      </p>
      <ErrorBanner message={error} />

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Settings</h3>
        {settings && (
          <>
            <div className="row">
              <label>
                Prefix
                <input
                  type="text"
                  value={settings.prefix}
                  onChange={(e) => setSettings({ ...settings, prefix: e.target.value })}
                />
              </label>
              <label>
                Path match
                <input
                  type="text"
                  value={settings.path_match}
                  onChange={(e) => setSettings({ ...settings, path_match: e.target.value })}
                />
              </label>
            </div>
            <button onClick={saveSettings}>Save settings</button>
          </>
        )}
      </div>

      <div className="panel">
        <div className="row">
          <label style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
            <input type="checkbox" checked={undo} onChange={(e) => setUndo(e.target.checked)} />
            Undo (remove the prefix and comment instead)
          </label>
        </div>
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
                  <td>{i.fail && <span className="chip bad">{i.fail}</span>}</td>
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
