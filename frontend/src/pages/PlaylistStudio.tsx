import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { api } from "../api/client";
import type { StudioDiff, StudioEntry, StudioTrack } from "../api/types";
import ErrorBanner from "../components/ErrorBanner";
import { useApiError } from "../hooks/useApiError";

type Mode = "instant" | "alchemy";
type Variety = "tight" | "balanced" | "wide";

function trackLabel(t: StudioTrack): string {
  return t.artist ? `${t.title} — ${t.artist}` : t.title;
}

export default function PlaylistStudioPage() {
  const { error, run } = useApiError();
  const location = useLocation();

  const [mode, setMode] = useState<Mode>("instant");
  const [prompt, setPrompt] = useState("");

  const [anchorQuery, setAnchorQuery] = useState("");
  const [anchorResults, setAnchorResults] = useState<StudioTrack[]>([]);
  const [anchors, setAnchors] = useState<StudioTrack[]>([]);
  const [excludes, setExcludes] = useState<StudioTrack[]>([]);
  const [size, setSize] = useState(30);
  const [variety, setVariety] = useState<Variety>("balanced");

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [current, setCurrent] = useState<StudioEntry | null>(null);
  const [diff, setDiff] = useState<StudioDiff | null>(null);
  const [history, setHistory] = useState<StudioEntry[]>([]);
  const [instruction, setInstruction] = useState("");
  const [busy, setBusy] = useState(false);

  const [playlistName, setPlaylistName] = useState("");
  const [created, setCreated] = useState<string | null>(null);

  useEffect(() => {
    const seed = (location.state as { seedPrompt?: string } | null)?.seedPrompt;
    if (seed) {
      setMode("instant");
      setPrompt(seed);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadHistory = (sid: string) =>
    run(() => api.get<{ history: StudioEntry[] }>(`/api/playlist-studio/history/${encodeURIComponent(sid)}`))
      .then((r) => r && setHistory(r.history));

  const searchAnchors = (q: string) => {
    setAnchorQuery(q);
    if (!q.trim()) {
      setAnchorResults([]);
      return;
    }
    run(() => api.get<{ tracks: StudioTrack[] }>(`/api/playlist-studio/anchors/search?q=${encodeURIComponent(q)}`))
      .then((r) => r && setAnchorResults(r.tracks));
  };

  const addAnchor = (t: StudioTrack) => {
    if (!anchors.some((a) => a.id === t.id)) setAnchors([...anchors, t]);
  };
  const addExclude = (t: StudioTrack) => {
    if (!excludes.some((e) => e.id === t.id)) setExcludes([...excludes, t]);
  };

  const generate = () => {
    setBusy(true);
    setDiff(null);
    const req =
      mode === "instant"
        ? api.post<{ session_id: string; entry: StudioEntry }>("/api/playlist-studio/generate/instant", {
            prompt,
            session_id: sessionId,
          })
        : api.post<{ session_id: string; entry: StudioEntry }>("/api/playlist-studio/generate/alchemy", {
            anchors,
            excludes,
            size,
            variety,
            session_id: sessionId,
          });
    run(() => req)
      .then((r) => {
        if (!r) return;
        setSessionId(r.session_id);
        setCurrent(r.entry);
        setCreated(null);
        loadHistory(r.session_id);
      })
      .finally(() => setBusy(false));
  };

  const refine = () => {
    if (!sessionId || !instruction.trim()) return;
    setBusy(true);
    run(() =>
      api.post<{ entry: StudioEntry; diff: StudioDiff }>("/api/playlist-studio/refine", {
        session_id: sessionId,
        instruction,
      }),
    )
      .then((r) => {
        if (!r) return;
        setCurrent(r.entry);
        setDiff(r.diff);
        setInstruction("");
        loadHistory(sessionId);
      })
      .finally(() => setBusy(false));
  };

  const createPlaylist = () => {
    if (!sessionId || !current || !playlistName) return;
    run(() =>
      api.post("/api/playlist-studio/create-playlist", {
        session_id: sessionId,
        entry_id: current.id,
        playlist_name: playlistName,
      }),
    ).then((r) => r !== undefined && setCreated(playlistName));
  };

  const movedIds = useMemo(() => new Set((diff?.moved ?? []).map((t) => t.id)), [diff]);
  const addedIds = useMemo(() => new Set((diff?.added ?? []).map((t) => t.id)), [diff]);

  return (
    <div>
      <h2>Playlist Studio</h2>
      <ErrorBanner message={error} />

      <div className="panel">
        <div className="row">
          <button className={mode === "instant" ? "primary" : ""} onClick={() => setMode("instant")}>
            Instant
          </button>
          <button className={mode === "alchemy" ? "primary" : ""} onClick={() => setMode("alchemy")}>
            Alchemy
          </button>
        </div>

        {mode === "instant" ? (
          <label>
            Describe the playlist
            <textarea
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Upbeat road trip music, mostly 2000s to today, max 2 songs per artist, no live versions"
            />
          </label>
        ) : (
          <>
            <p className="muted">
              Alchemy blends the artists of your chosen anchor tracks into one Instant Playlist request -
              AudioMuse has no confirmed public API for its own Song Alchemy feature, so this composes the
              closest equivalent from a documented, working one.
            </p>
            <input
              type="text"
              placeholder="Search your library for anchor tracks…"
              value={anchorQuery}
              onChange={(e) => searchAnchors(e.target.value)}
              style={{ width: "100%", marginBottom: 10 }}
            />
            {anchorResults.length > 0 && (
              <div style={{ maxHeight: 160, overflowY: "auto", border: "1px solid var(--border)",
                            borderRadius: 8, marginBottom: 10 }}>
                <table>
                  <tbody>
                    {anchorResults.map((t) => (
                      <tr key={t.id}>
                        <td>{trackLabel(t)}</td>
                        <td style={{ whiteSpace: "nowrap" }}>
                          <button onClick={() => addAnchor(t)}>+ Include</button>{" "}
                          <button onClick={() => addExclude(t)}>+ Exclude</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div className="row">
              <div style={{ flex: 1 }}>
                <p className="muted">Include ({anchors.length})</p>
                {anchors.map((t) => (
                  <p key={t.id} className="chip good">
                    {trackLabel(t)}{" "}
                    <button onClick={() => setAnchors(anchors.filter((a) => a.id !== t.id))}>✕</button>
                  </p>
                ))}
              </div>
              <div style={{ flex: 1 }}>
                <p className="muted">Exclude ({excludes.length})</p>
                {excludes.map((t) => (
                  <p key={t.id} className="chip bad">
                    {trackLabel(t)}{" "}
                    <button onClick={() => setExcludes(excludes.filter((e) => e.id !== t.id))}>✕</button>
                  </p>
                ))}
              </div>
            </div>
            <div className="row">
              <label style={{ flex: 1 }}>
                Size
                <input type="number" min={5} max={200} value={size}
                       onChange={(e) => setSize(Number(e.target.value))} />
              </label>
              <label style={{ flex: 1 }}>
                Variety
                <select value={variety} onChange={(e) => setVariety(e.target.value as Variety)}>
                  <option value="tight">Tighter matches</option>
                  <option value="balanced">Balanced</option>
                  <option value="wide">More variety</option>
                </select>
              </label>
            </div>
          </>
        )}

        <div className="row" style={{ marginTop: 10 }}>
          <button
            className="primary"
            disabled={busy || (mode === "instant" ? !prompt.trim() : anchors.length === 0)}
            onClick={generate}
          >
            {busy ? "Generating…" : sessionId ? "Generate again" : "Generate"}
          </button>
        </div>
      </div>

      {current && (
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>Result ({current.tracks.length} songs)</h3>
          <table>
            <tbody>
              {current.tracks.map((t) => (
                <tr key={t.id}>
                  <td
                    style={{
                      color: addedIds.has(t.id) ? "var(--good)" : undefined,
                      fontWeight: movedIds.has(t.id) ? 600 : undefined,
                    }}
                  >
                    {trackLabel(t)}
                    {addedIds.has(t.id) && " (new)"}
                    {movedIds.has(t.id) && !addedIds.has(t.id) && " (moved)"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {diff && diff.removed.length > 0 && (
            <>
              <p className="muted">Removed by that refinement:</p>
              {diff.removed.map((t) => (
                <p key={t.id} className="chip bad" style={{ textDecoration: "line-through" }}>
                  {trackLabel(t)}
                </p>
              ))}
            </>
          )}

          <div className="row" style={{ marginTop: 10 }}>
            <input
              type="text"
              placeholder="Refine: e.g. “more upbeat”, “less rap”, “swap in more 90s”"
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              style={{ flex: 1 }}
            />
            <button disabled={busy || !instruction.trim()} onClick={refine}>
              Apply refinement
            </button>
          </div>

          <div className="row" style={{ marginTop: 10 }}>
            <label style={{ flex: 1 }}>
              Playlist name
              <input type="text" value={playlistName} onChange={(e) => setPlaylistName(e.target.value)} />
            </label>
            <button className="primary" disabled={!playlistName} onClick={createPlaylist}>
              Create playlist
            </button>
          </div>
          {created && <p className="chip good">Created "{created}"</p>}
        </div>
      )}

      {history.length > 1 && (
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>History (this session)</h3>
          <table>
            <tbody>
              {history.map((h) => (
                <tr
                  key={h.id}
                  onClick={() => {
                    setCurrent(h);
                    setDiff(null);
                  }}
                  style={{ cursor: "pointer", background: current?.id === h.id ? "var(--border)" : undefined }}
                >
                  <td>{h.kind}</td>
                  <td>{h.tracks.length} songs</td>
                  <td className="muted">{new Date(h.created * 1000).toLocaleTimeString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
