import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type {
  CoverBackground, CoverFont, CoverHistoryEntry, CoverLayout, CoverPlaylist, CoverStyle,
} from "../api/types";
import ErrorBanner from "../components/ErrorBanner";
import { useApiError } from "../hooks/useApiError";

type Mode = "template" | "ai";

function bgImageUrl(id: string) {
  return `/api/playlist-covers/backgrounds/image?id=${encodeURIComponent(id)}`;
}

function historyImageUrl(playlistId: string, entryId: string) {
  return `/api/playlist-covers/history/${encodeURIComponent(playlistId)}/${encodeURIComponent(entryId)}/image`;
}

export default function CoverArtPage() {
  const { error, run } = useApiError();
  const [playlists, setPlaylists] = useState<CoverPlaylist[]>([]);
  const [playlistFilter, setPlaylistFilter] = useState("");
  const [selected, setSelected] = useState<CoverPlaylist | null>(null);

  const [styles, setStyles] = useState<CoverStyle[]>([]);
  const [aiAvailable, setAiAvailable] = useState(false);
  const [layouts, setLayouts] = useState<CoverLayout[]>([]);
  const [fonts, setFonts] = useState<CoverFont[]>([]);
  const [backgrounds, setBackgrounds] = useState<CoverBackground[]>([]);
  const [bgFilter, setBgFilter] = useState("");

  const [mode, setMode] = useState<Mode>("template");
  const [layout, setLayout] = useState("bottom-banner");
  const [font, setFont] = useState<string | null>(null);
  const [style, setStyle] = useState("dynamic");
  const [includeTracks, setIncludeTracks] = useState(true);
  const [backgroundId, setBackgroundId] = useState<string | null>(null);

  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<CoverHistoryEntry | null>(null);
  const [history, setHistory] = useState<CoverHistoryEntry[]>([]);
  const [applyResult, setApplyResult] = useState<string | null>(null);

  useEffect(() => {
    run(() => api.get<{ playlists: CoverPlaylist[]; error: string | null }>("/api/playlist-covers/playlists"))
      .then((r) => r && setPlaylists(r.playlists));
    run(() => api.get<{ styles: CoverStyle[]; ai_available: boolean }>("/api/playlist-covers/styles")).then(
      (r) => {
        if (!r) return;
        setStyles(r.styles);
        setAiAvailable(r.ai_available);
      },
    );
    run(() => api.get<{ layouts: CoverLayout[] }>("/api/playlist-covers/layouts")).then((r) => r && setLayouts(r.layouts));
    run(() => api.get<{ fonts: CoverFont[] }>("/api/playlist-covers/fonts")).then((r) => r && setFonts(r.fonts));
    run(() => api.get<{ backgrounds: CoverBackground[] }>("/api/playlist-covers/backgrounds")).then(
      (r) => r && setBackgrounds(r.backgrounds),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadHistory = (playlistId: string) =>
    run(() => api.get<{ history: CoverHistoryEntry[] }>(`/api/playlist-covers/history/${encodeURIComponent(playlistId)}`))
      .then((r) => r && setHistory(r.history));

  const selectPlaylist = (p: CoverPlaylist) => {
    setSelected(p);
    setPreview(null);
    setApplyResult(null);
    loadHistory(p.id);
  };

  const filteredPlaylists = useMemo(() => {
    const q = playlistFilter.trim().toLowerCase();
    if (!q) return playlists;
    return playlists.filter((p) => p.name.toLowerCase().includes(q));
  }, [playlists, playlistFilter]);

  const filteredBackgrounds = useMemo(() => {
    const q = bgFilter.trim().toLowerCase();
    if (!q) return backgrounds;
    return backgrounds.filter((b) => b.name.toLowerCase().includes(q));
  }, [backgrounds, bgFilter]);

  const generate = () => {
    if (!selected) return;
    setBusy(true);
    const req =
      mode === "template"
        ? backgroundId &&
          api.post<CoverHistoryEntry>("/api/playlist-covers/generate/template", {
            playlist_id: selected.id,
            playlist_name: selected.name,
            background_id: backgroundId,
            layout,
            font,
          })
        : api.post<CoverHistoryEntry>("/api/playlist-covers/generate/ai", {
            playlist_id: selected.id,
            playlist_name: selected.name,
            style,
            include_tracks: includeTracks,
            layout,
            font,
          });
    if (!req) {
      setBusy(false);
      return;
    }
    run(() => req)
      .then((entry) => {
        if (!entry) return;
        setPreview(entry);
        loadHistory(selected.id);
      })
      .finally(() => setBusy(false));
  };

  const apply = () => {
    if (!selected || !preview) return;
    run(() =>
      api.post<{ method: string }>("/api/playlist-covers/apply", { playlist_id: selected.id, entry_id: preview.id }),
    ).then((r) => {
      if (!r) return;
      setApplyResult(
        r.method === "sidecar"
          ? "Applied: wrote a sidecar image next to the playlist's file. Navidrome should pick it up without a restart."
          : "Applied: uploaded directly to Navidrome via the playlist cover API.",
      );
      run(() => api.get<{ playlists: CoverPlaylist[]; error: string | null }>("/api/playlist-covers/playlists")).then(
        (r2) => r2 && setPlaylists(r2.playlists),
      );
    });
  };

  const removeCover = () => {
    if (!selected) return;
    run(() => api.post<{ method: string }>("/api/playlist-covers/remove", { playlist_id: selected.id })).then((r) => {
      if (!r) return;
      setApplyResult(`Removed (${r.method}). Navidrome will show its auto-generated cover again.`);
    });
  };

  return (
    <div>
      <h2>Playlist cover art</h2>
      <ErrorBanner message={error} />

      <div className="panel">
        <div className="row">
          <input
            type="text"
            placeholder="Search playlists…"
            value={playlistFilter}
            onChange={(e) => setPlaylistFilter(e.target.value)}
            style={{ minWidth: 260 }}
          />
          {selected && <span className="muted">Selected: {selected.name}</span>}
        </div>
        <div style={{ maxHeight: 180, overflowY: "auto", border: "1px solid var(--border)", borderRadius: 8 }}>
          <table>
            <tbody>
              {filteredPlaylists.slice(0, 300).map((p) => (
                <tr
                  key={p.id}
                  onClick={() => selectPlaylist(p)}
                  style={{ cursor: "pointer", background: selected?.id === p.id ? "var(--border)" : undefined }}
                >
                  <td>{p.name}</td>
                  <td className="muted">{p.file_backed ? "file-backed" : "Navidrome-only"}</td>
                  <td>{p.has_sidecar && <span className="chip good">cover set</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {selected && (
        <>
          <div className="panel">
            <div className="row">
              <button className={mode === "template" ? "primary" : ""} onClick={() => setMode("template")}>
                Template
              </button>
              <button
                className={mode === "ai" ? "primary" : ""}
                onClick={() => setMode("ai")}
                disabled={!aiAvailable}
                title={aiAvailable ? "" : "Set REPLICATE_API_TOKEN and REPLICATE_MODEL to enable AI mode"}
              >
                AI {!aiAvailable && "(not configured)"}
              </button>
            </div>

            <div className="row">
              <label style={{ flex: 1, minWidth: 220 }}>
                Layout
                <select value={layout} onChange={(e) => setLayout(e.target.value)}>
                  {layouts.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.label}
                    </option>
                  ))}
                </select>
              </label>
              <label style={{ flex: 1, minWidth: 220 }}>
                Font
                <select value={font ?? ""} onChange={(e) => setFont(e.target.value || null)}>
                  <option value="">Default for this layout</option>
                  {fonts.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.label} — {f.vibe}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <p className="muted">{layouts.find((l) => l.id === layout)?.description}</p>

            {mode === "template" ? (
              <>
                <input
                  type="text"
                  placeholder={`Search ${backgrounds.length} backgrounds (try "photo", "mesh", "contour", or a mood)…`}
                  value={bgFilter}
                  onChange={(e) => setBgFilter(e.target.value)}
                  style={{ width: "100%", marginBottom: 10 }}
                />
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fill, minmax(90px, 1fr))",
                    gap: 6,
                    maxHeight: 360,
                    overflowY: "auto",
                  }}
                >
                  {filteredBackgrounds.map((b) => (
                    <img
                      key={b.id}
                      src={bgImageUrl(b.id)}
                      loading="lazy"
                      alt={b.name}
                      title={b.name}
                      onClick={() => setBackgroundId(b.id)}
                      style={{
                        width: "100%",
                        aspectRatio: "1 / 1",
                        objectFit: "cover",
                        borderRadius: 6,
                        cursor: "pointer",
                        outline: backgroundId === b.id ? "3px solid var(--accent)" : "1px solid var(--border)",
                      }}
                    />
                  ))}
                </div>
              </>
            ) : (
              <>
                <div className="row">
                  <label style={{ flex: 1, minWidth: 220 }}>
                    Style
                    <select value={style} onChange={(e) => setStyle(e.target.value)}>
                      {styles.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
                    <input type="checkbox" checked={includeTracks} onChange={(e) => setIncludeTracks(e.target.checked)} />
                    Influence with track names
                  </label>
                </div>
                <p className="muted">{styles.find((s) => s.id === style)?.prompt}</p>
              </>
            )}

            <div className="row" style={{ marginTop: 10 }}>
              <button
                className="primary"
                disabled={busy || (mode === "template" && !backgroundId)}
                onClick={generate}
              >
                {busy ? "Generating…" : "Generate"}
              </button>
            </div>
          </div>

          {preview && (
            <div className="panel">
              <h3 style={{ marginTop: 0 }}>Preview</h3>
              <img
                src={historyImageUrl(selected.id, preview.id)}
                alt="Generated cover"
                style={{ width: 320, height: 320, borderRadius: 10, display: "block" }}
              />
              <div className="row" style={{ marginTop: 10 }}>
                <button className="primary" onClick={apply}>
                  Apply to Navidrome
                </button>
                <a href={historyImageUrl(selected.id, preview.id)} download={`${selected.name}.png`}>
                  <button>Download PNG</button>
                </a>
                <button onClick={removeCover}>Remove current cover</button>
              </div>
              {applyResult && <p className="chip good">{applyResult}</p>}
            </div>
          )}

          {history.length > 0 && (
            <div className="panel">
              <h3 style={{ marginTop: 0 }}>History</h3>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {history.map((h) => (
                  <img
                    key={h.id}
                    src={historyImageUrl(selected.id, h.id)}
                    alt={h.mode}
                    title={`${h.mode} · ${new Date(h.created * 1000).toLocaleString()}`}
                    onClick={() => setPreview(h)}
                    style={{
                      width: 90,
                      height: 90,
                      objectFit: "cover",
                      borderRadius: 6,
                      cursor: "pointer",
                      outline: preview?.id === h.id ? "3px solid var(--accent)" : "1px solid var(--border)",
                    }}
                  />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
