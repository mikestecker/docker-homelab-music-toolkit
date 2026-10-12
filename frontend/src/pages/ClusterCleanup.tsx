import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import ErrorBanner from "../components/ErrorBanner";
import LogPanel from "../components/LogPanel";
import { useApiError } from "../hooks/useApiError";

interface Settings {
  max_share: number;
  min_seconds: number;
  rename_prefix: string;
  scope: "christian" | "worship";
  reverse_cleanup: boolean;
}

interface Playlist {
  name: string;
  owner: string | null;
  owner_skipped: boolean;
  total_songs: number;
  worship_removed: number;
  short_removed: number;
  secular_removed: number;
  kept_worship_leaning: boolean;
  worship_share: number;
  renamed_to: string | null;
  removed_tracks: { title: string; artist: string; why: string; direction: string | null }[];
  error: string | null;
}

interface RunResult {
  dry_run: boolean;
  log: string[];
  playlists: Playlist[];
  total_removed: number;
  error: string | null;
}

export default function ClusterCleanupPage() {
  const { error, run } = useApiError();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [result, setResult] = useState<RunResult | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    run(() => api.get<Settings>("/api/cluster-cleanup/settings")).then((r) => r && setSettings(r));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const saveSettings = () =>
    settings &&
    run(() => api.put<Settings>("/api/cluster-cleanup/settings", settings)).then((r) => r && setSettings(r));

  const doRun = (apply: boolean) => {
    setBusy(true);
    run(() => api.post<RunResult>(`/api/cluster-cleanup/${apply ? "apply" : "preview"}`))
      .then((r) => r && setResult(r))
      .finally(() => setBusy(false));
  };

  return (
    <div>
      <h2>Cluster cleanup</h2>
      <p className="muted">
        Removes songs from AudioMuse's <code>_automatic</code> clustering playlists when the scoped set is a minority
        of the playlist. Always preview first. Manage the artist list itself on the{" "}
        <Link to="/christian-artists">Christian artists</Link> page.
      </p>
      <ErrorBanner message={error} />

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Settings</h3>
        {settings && (
          <>
            <div className="row">
              <label>
                Scope
                <select
                  value={settings.scope}
                  onChange={(e) => setSettings({ ...settings, scope: e.target.value as Settings["scope"] })}
                >
                  <option value="christian">Christian (all listed artists)</option>
                  <option value="worship">Worship only</option>
                </select>
              </label>
              <label>
                Max share (remove only below this)
                <input
                  type="number"
                  step="0.01"
                  min={0}
                  max={1}
                  value={settings.max_share}
                  onChange={(e) => setSettings({ ...settings, max_share: Number(e.target.value) })}
                />
              </label>
              <label>
                Min seconds (also drop shorter tracks)
                <input
                  type="number"
                  min={0}
                  value={settings.min_seconds}
                  onChange={(e) => setSettings({ ...settings, min_seconds: Number(e.target.value) })}
                />
              </label>
              <label>
                Rename prefix (optional folder)
                <input
                  type="text"
                  value={settings.rename_prefix}
                  onChange={(e) => setSettings({ ...settings, rename_prefix: e.target.value })}
                />
              </label>
            </div>
            <div className="row" style={{ marginTop: 10 }}>
              <label>
                <input
                  type="checkbox"
                  checked={settings.reverse_cleanup}
                  onChange={(e) => setSettings({ ...settings, reverse_cleanup: e.target.checked })}
                />{" "}
                Reverse cleanup: in a cluster where the scope is the majority, remove the secular minority instead
              </label>
            </div>
            <button onClick={saveSettings} style={{ marginTop: 10 }}>
              Save settings
            </button>
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
          {result && <span className="muted">Total removed: {result.total_removed}</span>}
        </div>
        {result && (
          <table style={{ marginTop: 10 }}>
            <thead>
              <tr>
                <th>Playlist</th>
                <th>Songs</th>
                <th>Removed (listed / secular / short)</th>
                <th>Kept as worship-leaning</th>
                <th>Renamed to</th>
              </tr>
            </thead>
            <tbody>
              {result.playlists.map((p) => (
                <tr key={p.name}>
                  <td>{p.name}</td>
                  <td>{p.total_songs}</td>
                  <td>
                    {p.worship_removed} / {p.secular_removed} / {p.short_removed}
                  </td>
                  <td>{p.kept_worship_leaning ? <span className="chip warn">yes</span> : ""}</td>
                  <td>{p.renamed_to ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {result && result.playlists.some((p) => p.removed_tracks.length > 0) && (
          <details style={{ marginTop: 10 }}>
            <summary className="muted" style={{ cursor: "pointer" }}>
              Removed tracks, by direction
            </summary>
            <table style={{ marginTop: 10 }}>
              <thead>
                <tr>
                  <th>Playlist</th>
                  <th>Track</th>
                  <th>Artist</th>
                  <th>Why</th>
                </tr>
              </thead>
              <tbody>
                {result.playlists.flatMap((p) =>
                  p.removed_tracks.map((t, i) => (
                    <tr key={`${p.name}-${i}`}>
                      <td className="muted">{p.name}</td>
                      <td>{t.title}</td>
                      <td>{t.artist}</td>
                      <td>
                        <span className={`chip ${t.direction === "secular_minority" ? "bad" : "warn"}`}>{t.why}</span>
                      </td>
                    </tr>
                  )),
                )}
              </tbody>
            </table>
          </details>
        )}
        <LogPanel lines={result?.log} />
      </div>
    </div>
  );
}
