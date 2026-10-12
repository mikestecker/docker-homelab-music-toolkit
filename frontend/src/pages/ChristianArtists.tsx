import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { ArtistRow, ChristianSettings, MigrationLog, ScanResult, SeedDiff } from "../api/types";
import ErrorBanner from "../components/ErrorBanner";
import LogPanel from "../components/LogPanel";
import ToastView from "../components/Toast";
import { useApiError } from "../hooks/useApiError";
import { useToast } from "../hooks/useToast";

interface RunResult {
  dry_run: boolean;
  log: string[];
  changed: number;
  unchanged: number;
  errors: number;
  counts: { christian: number; worship: number };
  error: string | null;
}

interface BulkReport {
  added: string[];
  duplicates: string[];
}

export default function ChristianArtistsPage() {
  const { error, run } = useApiError();
  const toast = useToast();

  const [settings, setSettings] = useState<ChristianSettings | null>(null);
  const [rows, setRows] = useState<ArtistRow[]>([]);
  const [scan, setScan] = useState<ScanResult | null>(null);
  const [seedDiff, setSeedDiff] = useState<SeedDiff | null>(null);
  const [migrationLog, setMigrationLog] = useState<MigrationLog | null>(null);
  const [overridesText, setOverridesText] = useState("");
  const [result, setResult] = useState<RunResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [scanning, setScanning] = useState(false);

  const [query, setQuery] = useState("");
  const [genreFilter, setGenreFilter] = useState("");
  const [tierFilter, setTierFilter] = useState("");
  const [enabledFilter, setEnabledFilter] = useState("");
  const [worshipFilter, setWorshipFilter] = useState("");
  const [libraryFilter, setLibraryFilter] = useState("");

  const [newArtist, setNewArtist] = useState({ artist: "", genre: "", worship: "no", tier: "core", enabled: true });
  const [bulkText, setBulkText] = useState("");
  const [bulkGenre, setBulkGenre] = useState("");
  const [bulkWorship, setBulkWorship] = useState("no");
  const [bulkReport, setBulkReport] = useState<BulkReport | null>(null);

  const loadRows = () =>
    run(() => api.get<{ rows: ArtistRow[] }>("/api/christian-artists/artists")).then((r) => r && setRows(r.rows));
  const loadScan = () =>
    run(() => api.get<ScanResult | null>("/api/christian-artists/scan")).then((r) => setScan(r ?? null));
  const loadSeedDiff = () =>
    run(() => api.get<SeedDiff>("/api/christian-artists/seed-diff")).then((r) => r && setSeedDiff(r));

  useEffect(() => {
    run(() => api.get<ChristianSettings>("/api/christian-artists/settings")).then((r) => r && setSettings(r));
    loadRows();
    loadScan();
    loadSeedDiff();
    run(() => api.get<MigrationLog | null>("/api/christian-artists/migration-log")).then((r) => setMigrationLog(r ?? null));
    run(() => api.get<{ text: string }>("/api/christian-artists/overrides")).then((r) => r && setOverridesText(r.text));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const genres = useMemo(() => Array.from(new Set(rows.map((r) => r.genre).filter(Boolean))).sort(), [rows]);
  const tiers = useMemo(() => Array.from(new Set(rows.map((r) => r.tier).filter(Boolean))).sort(), [rows]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((r) => {
      if (genreFilter && r.genre !== genreFilter) return false;
      if (tierFilter && r.tier !== tierFilter) return false;
      if (enabledFilter && r.enabled !== enabledFilter) return false;
      if (worshipFilter && r.worship !== worshipFilter) return false;
      const inLibrary = (scan?.library_counts[r.artist] ?? 0) > 0;
      if (libraryFilter === "in" && !inLibrary) return false;
      if (libraryFilter === "out" && inLibrary) return false;
      if (q && !r.artist.toLowerCase().includes(q) && !(r.notes || "").toLowerCase().includes(q)) return false;
      return true;
    });
  }, [rows, query, genreFilter, tierFilter, enabledFilter, worshipFilter, libraryFilter, scan]);

  const saveSettings = (patch: Partial<ChristianSettings>) => {
    if (!settings) return;
    const next = { ...settings, ...patch };
    setSettings(next);
    run(() => api.put<ChristianSettings>("/api/christian-artists/settings", next));
  };

  const updateField = (artist: string, field: string, value: string) => {
    setRows((rs) => rs.map((r) => (r.artist === artist ? { ...r, [field]: value } : r)));
    run(() => api.put("/api/christian-artists/artists", { name: artist, [field]: value }));
  };

  const addArtist = () => {
    if (!newArtist.artist.trim()) return;
    run(() => api.post("/api/christian-artists/artists", newArtist)).then((r) => {
      if (r === undefined) return;
      toast.show({ tone: "good", message: `Added "${newArtist.artist}".` });
      setNewArtist({ artist: "", genre: "", worship: "no", tier: "core", enabled: true });
      loadRows();
    });
  };

  const deleteArtist = (artist: string) => {
    run(() => api.post("/api/christian-artists/artists/delete", { name: artist })).then(() => loadRows());
  };

  const bulkAdd = () => {
    const names = bulkText
      .split("\n")
      .map((n) => n.trim())
      .filter(Boolean);
    if (names.length === 0) return;
    run(() =>
      api.post<BulkReport>("/api/christian-artists/artists/bulk", { names, genre: bulkGenre, worship: bulkWorship }),
    ).then((r) => {
      if (!r) return;
      setBulkReport(r);
      toast.show({
        tone: "good",
        message: `Added ${r.added.length}, skipped ${r.duplicates.length} duplicate${r.duplicates.length === 1 ? "" : "s"}.`,
      });
      setBulkText("");
      loadRows();
    });
  };

  const addSuggestion = (name: string, genre: string) => {
    run(() => api.post("/api/christian-artists/artists", { artist: name, genre, worship: "no" })).then((r) => {
      if (r !== undefined) loadRows();
    });
  };

  const doScan = () => {
    setScanning(true);
    run(() => api.post<ScanResult>("/api/christian-artists/scan"))
      .then((r) => r && setScan(r))
      .finally(() => setScanning(false));
  };

  const saveOverrides = () => run(() => api.put("/api/christian-artists/overrides", { text: overridesText }));

  const resetToDefaults = () => {
    if (
      !window.confirm(
        "Add any new artists from the shipped default list? This never changes or removes your existing entries.",
      )
    )
      return;
    run(() => api.post<{ added: number }>("/api/christian-artists/reset-to-defaults")).then((r) => {
      if (!r) return;
      toast.show({ tone: "good", message: `Added ${r.added} new artist${r.added === 1 ? "" : "s"} from the default list.` });
      loadRows();
      loadSeedDiff();
    });
  };

  const doRun = (apply: boolean) => {
    setBusy(true);
    run(() => api.post<RunResult>(`/api/christian-artists/${apply ? "apply" : "preview"}`))
      .then((r) => r && setResult(r))
      .finally(() => setBusy(false));
  };

  return (
    <div>
      <h2>Christian artists</h2>
      <p className="muted">
        One allowlist drives the <code>CATEGORY</code> file tag, Cluster Cleanup's scope, and the Content filter on
        AudioMuse-generated playlists.
      </p>
      <ErrorBanner message={error} />

      {migrationLog?.changed && (
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>Migrated from your old worship artist list</h3>
          <p className="muted">
            {migrationLog.worship_enabled.length} artist{migrationLog.worship_enabled.length === 1 ? "" : "s"} set to
            worship, {migrationLog.disabled.length} disabled - based on how you'd edited{" "}
            <code>worship-artists.txt</code> (kept as <code>worship-artists.txt.migrated</code>).
          </p>
        </div>
      )}

      {seedDiff && seedDiff.new_count > 0 && (
        <div className="panel">
          <p style={{ margin: 0 }}>
            {seedDiff.new_count} new artist{seedDiff.new_count === 1 ? "" : "s"} available from the updated default
            list. <button onClick={resetToDefaults}>Review &amp; add</button>
          </p>
        </div>
      )}

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Settings</h3>
        {settings && (
          <label>
            <input
              type="checkbox"
              checked={settings.prune}
              onChange={(e) => saveSettings({ prune: e.target.checked })}
            />{" "}
            Prune: remove <code>christian</code>/<code>worship</code> from files whose artist is no longer on the list
          </label>
        )}
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Add an artist</h3>
        <div className="row">
          <input
            type="text"
            placeholder="Artist name"
            value={newArtist.artist}
            onChange={(e) => setNewArtist({ ...newArtist, artist: e.target.value })}
            style={{ flex: 1 }}
          />
          <input
            type="text"
            placeholder="Genre"
            value={newArtist.genre}
            onChange={(e) => setNewArtist({ ...newArtist, genre: e.target.value })}
          />
          <select value={newArtist.worship} onChange={(e) => setNewArtist({ ...newArtist, worship: e.target.value })}>
            <option value="no">Not worship</option>
            <option value="yes">Worship</option>
            <option value="unknown">Unknown</option>
          </select>
          <label>
            <input
              type="checkbox"
              checked={newArtist.enabled}
              onChange={(e) => setNewArtist({ ...newArtist, enabled: e.target.checked })}
            />{" "}
            Enabled
          </label>
          <button onClick={addArtist}>Add</button>
        </div>
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Bulk add</h3>
        <p className="muted">Paste one artist name per line. Duplicates (by normalized name) are skipped and reported.</p>
        <textarea
          rows={6}
          value={bulkText}
          onChange={(e) => setBulkText(e.target.value)}
          placeholder={"Artist One\nArtist Two"}
        />
        <div className="row" style={{ marginTop: 8 }}>
          <input type="text" placeholder="Genre (optional)" value={bulkGenre} onChange={(e) => setBulkGenre(e.target.value)} />
          <select value={bulkWorship} onChange={(e) => setBulkWorship(e.target.value)}>
            <option value="no">Not worship</option>
            <option value="yes">Worship</option>
          </select>
          <button onClick={bulkAdd}>Add batch</button>
        </div>
        {bulkReport && (
          <p className="muted">
            Added {bulkReport.added.length}.
            {bulkReport.duplicates.length > 0 && ` Skipped: ${bulkReport.duplicates.join(", ")}`}
          </p>
        )}
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Library scan</h3>
        <p className="muted">Reads tags only - no changes are made. Powers the "tracks in library" column below.</p>
        <div className="row">
          <button disabled={scanning} onClick={doScan}>
            {scanning ? "Scanning…" : "Scan library"}
          </button>
        </div>
        {scan && (
          <>
            {scan.needs_decision.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <strong>Needs a decision ({scan.needs_decision.length})</strong>
                <table>
                  <thead>
                    <tr>
                      <th>Artist</th>
                      <th>Sample albums</th>
                      <th>MBID</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {scan.needs_decision.map((d) => (
                      <tr key={d.name}>
                        <td>{d.name}</td>
                        <td className="muted">{d.albums.join(", ")}</td>
                        <td className="muted">{d.mbid_suggestion ?? ""}</td>
                        <td style={{ whiteSpace: "nowrap" }}>
                          <button onClick={() => updateField(d.name, "enabled", "yes")}>Enable</button>{" "}
                          <button onClick={() => updateField(d.name, "enabled", "no")}>Keep disabled</button>{" "}
                          {d.mbid_suggestion && (
                            <button onClick={() => updateField(d.name, "mbid", d.mbid_suggestion as string)}>
                              Set MBID
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {scan.suggestions.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <strong>Suggestions ({scan.suggestions.length})</strong>
                <table>
                  <thead>
                    <tr>
                      <th>Artist</th>
                      <th>Genre tags</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {scan.suggestions.map((s) => (
                      <tr key={s.name}>
                        <td>{s.name}</td>
                        <td className="muted">{s.genres.join(", ")}</td>
                        <td>
                          <button onClick={() => addSuggestion(s.name, s.genres[0] || "")}>Add</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {scan.not_in_library.length > 0 && (
              <details style={{ marginTop: 12 }}>
                <summary className="muted" style={{ cursor: "pointer" }}>
                  Not in library ({scan.not_in_library.length})
                </summary>
                <p className="muted">{scan.not_in_library.join(", ")}</p>
              </details>
            )}
          </>
        )}
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>
          Artists ({filtered.length} of {rows.length})
        </h3>
        <div className="row">
          <input
            type="text"
            placeholder="Search artist or notes"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{ flex: 1 }}
          />
          <select value={genreFilter} onChange={(e) => setGenreFilter(e.target.value)}>
            <option value="">Any genre</option>
            {genres.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
          <select value={tierFilter} onChange={(e) => setTierFilter(e.target.value)}>
            <option value="">Any tier</option>
            {tiers.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <select value={enabledFilter} onChange={(e) => setEnabledFilter(e.target.value)}>
            <option value="">Enabled: any</option>
            <option value="yes">Enabled</option>
            <option value="no">Disabled</option>
          </select>
          <select value={worshipFilter} onChange={(e) => setWorshipFilter(e.target.value)}>
            <option value="">Worship: any</option>
            <option value="yes">Worship</option>
            <option value="no">Not worship</option>
            <option value="unknown">Unknown worship</option>
          </select>
          <select value={libraryFilter} onChange={(e) => setLibraryFilter(e.target.value)}>
            <option value="">In library: any</option>
            <option value="in">In library</option>
            <option value="out">Not in library</option>
          </select>
        </div>
        <table style={{ marginTop: 10 }}>
          <thead>
            <tr>
              <th>Artist</th>
              <th>Genre</th>
              <th>Worship</th>
              <th>Tier</th>
              <th>Enabled</th>
              <th>MBID</th>
              <th>Tracks</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 1000).map((r) => (
              <tr key={r.artist}>
                <td>
                  {r.artist}{" "}
                  {r.ambiguous === "yes" && (
                    <span className="chip warn" title={r.notes || "ambiguous name"}>
                      ambiguous
                    </span>
                  )}
                </td>
                <td>
                  <input
                    type="text"
                    value={r.genre}
                    style={{ width: 90 }}
                    onChange={(e) => updateField(r.artist, "genre", e.target.value)}
                  />
                </td>
                <td>
                  <select value={r.worship} onChange={(e) => updateField(r.artist, "worship", e.target.value)}>
                    <option value="yes">yes</option>
                    <option value="no">no</option>
                    <option value="unknown">unknown</option>
                  </select>
                </td>
                <td className="muted">{r.tier}</td>
                <td>
                  <input
                    type="checkbox"
                    checked={r.enabled === "yes"}
                    onChange={(e) => updateField(r.artist, "enabled", e.target.checked ? "yes" : "no")}
                  />
                </td>
                <td>
                  <input
                    type="text"
                    value={r.mbid}
                    style={{ width: 90 }}
                    onChange={(e) => updateField(r.artist, "mbid", e.target.value)}
                  />
                </td>
                <td className="muted">{scan?.library_counts[r.artist] ?? "-"}</td>
                <td>
                  <button onClick={() => deleteArtist(r.artist)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length > 1000 && (
          <p className="muted">Showing the first 1,000 of {filtered.length} - narrow your search to see more.</p>
        )}
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Worship overrides</h3>
        <p className="muted">
          For the exceptions: one album or track by an otherwise non-worship Christian artist that counts as worship
          (or, with a leading <code>!</code>, the reverse). <code>Artist | Album</code> or{" "}
          <code>Artist | Album | Title</code>, one per line.
        </p>
        <textarea rows={8} value={overridesText} onChange={(e) => setOverridesText(e.target.value)} />
        <div className="row" style={{ marginTop: 10 }}>
          <button onClick={saveOverrides}>Save overrides</button>
        </div>
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Tagging</h3>
        <p className="muted">Writes the CATEGORY tag on your music files. Always preview first.</p>
        <div className="row">
          <button disabled={busy} onClick={() => doRun(false)}>
            Preview
          </button>
          <button className="primary" disabled={busy} onClick={() => doRun(true)}>
            Apply
          </button>
          {result && (
            <span className="muted">
              {result.changed} to change, {result.unchanged} already correct, {result.errors} errors
            </span>
          )}
        </div>
        <LogPanel lines={result?.log} />
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Export / reset</h3>
        <div className="row">
          <button onClick={() => (window.location.href = "/api/christian-artists/export")}>Export CSV</button>
          <button onClick={resetToDefaults}>Reset to defaults (merge new only)</button>
        </div>
      </div>

      {toast.toast && (
        <div className="dock">
          <ToastView toast={toast.toast} onDismiss={toast.dismiss} />
        </div>
      )}
    </div>
  );
}
