import { useEffect, useState } from "react";
import { api } from "../api/client";
import ErrorBanner from "../components/ErrorBanner";
import LogPanel from "../components/LogPanel";
import { useApiError } from "../hooks/useApiError";

interface Settings {
  playlists_dir: string;
  host_music_root: string;
}

interface PlaylistFix {
  name: string;
  fixed: { old: string; new: string; note: string }[];
  missing: { old: string; why: string }[];
  backup: string | null;
}

interface RunResult {
  dry_run: boolean;
  log: string[];
  playlists: PlaylistFix[];
  totals: { fixed: number; missing: number; files: number };
  error: string | null;
}

export default function M3uFixPage() {
  const { error, run } = useApiError();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [result, setResult] = useState<RunResult | null>(null);
  const [backups, setBackups] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  const loadBackups = () => run(() => api.get<{ backups: string[] }>("/api/m3u-fix/backups")).then((r) => r && setBackups(r.backups));

  useEffect(() => {
    run(() => api.get<Settings>("/api/m3u-fix/settings")).then((r) => r && setSettings(r));
    loadBackups();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const saveSettings = () =>
    settings && run(() => api.put<Settings>("/api/m3u-fix/settings", settings)).then((r) => r && setSettings(r));

  const doRun = (apply: boolean) => {
    setBusy(true);
    run(() => api.post<RunResult>(`/api/m3u-fix/${apply ? "apply" : "preview"}`))
      .then((r) => {
        if (r) setResult(r);
        if (apply) loadBackups();
      })
      .finally(() => setBusy(false));
  };

  const deleteBackup = (name: string) =>
    run(() => api.post("/api/m3u-fix/backups/delete", { name })).then(() => loadBackups());

  return (
    <div>
      <h2>Fix m3u paths</h2>
      <p className="muted">
        Repoints broken <code>.m3u</code> entries at the files you have now, matching by artist folder and track
        title. Every change keeps a timestamped backup of the original playlist.
      </p>
      <ErrorBanner message={error} />

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Settings</h3>
        {settings && (
          <>
            <div className="row">
              <label style={{ flex: 1 }}>
                Playlists folder
                <input
                  type="text"
                  value={settings.playlists_dir}
                  onChange={(e) => setSettings({ ...settings, playlists_dir: e.target.value })}
                />
              </label>
              <label style={{ flex: 1 }}>
                Host music root (for old host-style paths)
                <input
                  type="text"
                  value={settings.host_music_root}
                  onChange={(e) => setSettings({ ...settings, host_music_root: e.target.value })}
                />
              </label>
            </div>
            <button onClick={saveSettings}>Save settings</button>
          </>
        )}
      </div>

      <div className="panel">
        <div className="row">
          <button disabled={busy} onClick={() => doRun(false)}>
            Preview
          </button>
          <button className="primary" disabled={busy} onClick={() => doRun(true)}>
            Apply
          </button>
          {result && (
            <span className="muted">
              Fixed {result.totals.fixed}, missing {result.totals.missing}, across {result.totals.files} playlists
            </span>
          )}
        </div>
        {result?.playlists.map((p) => (
          <div key={p.name} style={{ marginTop: 10 }}>
            <strong>{p.name}</strong>{" "}
            {p.backup && <span className="chip good">backup: {p.backup}</span>}
            <table>
              <tbody>
                {p.fixed.map((f, i) => (
                  <tr key={`f-${i}`}>
                    <td className="muted">{f.old}</td>
                    <td>→ {f.new}</td>
                    <td className="muted">{f.note}</td>
                  </tr>
                ))}
                {p.missing.map((m, i) => (
                  <tr key={`m-${i}`}>
                    <td className="muted">{m.old}</td>
                    <td>
                      <span className="chip warn">no match</span>
                    </td>
                    <td className="muted">{m.why}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
        <LogPanel lines={result?.log} />
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Backups</h3>
        {backups.length === 0 && <p className="muted">None.</p>}
        <ul>
          {backups.map((b) => (
            <li key={b}>
              {b} <button onClick={() => deleteBackup(b)}>Delete</button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
