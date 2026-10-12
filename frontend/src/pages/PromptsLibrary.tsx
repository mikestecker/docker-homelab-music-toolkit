import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { ContentFilter, Recipe, SeedPrompt } from "../api/types";
import Drawer from "../components/Drawer";
import ErrorBanner from "../components/ErrorBanner";
import { useApiError } from "../hooks/useApiError";

type Tab = "prompts" | "recipes";

const CONTENT_FILTER_LABELS: Record<ContentFilter, string> = {
  any: "Any",
  christian: "Christian only",
  worship: "Worship only",
  no_christian: "No Christian",
};

// AudioMuse's chatPlaylist response shape isn't fully confirmed against its
// live /apidocs/ - this reads a few likely id/title/artist field names
// defensively rather than assuming one exact schema.
interface Song {
  [key: string]: unknown;
}

function songId(s: Song): string | undefined {
  const v = s.item_id ?? s.id ?? s.song_id ?? s.ItemId;
  return v === undefined ? undefined : String(v);
}
function songLabel(s: Song): string {
  const title = s.title ?? s.Title ?? s.name ?? "Untitled";
  const artist = s.artist ?? s.Artist ?? "";
  return artist ? `${title} — ${artist}` : String(title);
}
export default function PromptsLibraryPage() {
  const { error, run, setError } = useApiError();
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("prompts");
  const [prompts, setPrompts] = useState<SeedPrompt[]>([]);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState<{ name: string; prompt: string; faith?: boolean } | null>(null);
  const [songs, setSongs] = useState<Song[] | null>(null);
  const [filteredOut, setFilteredOut] = useState<Song[]>([]);
  const [short, setShort] = useState(false);
  const [rawResponse, setRawResponse] = useState<unknown>(null);
  const [playlistName, setPlaylistName] = useState("");
  const [running, setRunning] = useState(false);
  const [created, setCreated] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [contentFilter, setContentFilter] = useState<ContentFilter>("any");

  useEffect(() => {
    run(() => api.get<SeedPrompt[]>("/api/prompts/seedprompts")).then((r) => r && setPrompts(r));
    run(() => api.get<Recipe[]>("/api/prompts/recipes")).then((r) => r && setRecipes(r));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const items = tab === "prompts" ? prompts : recipes;
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((i) => i.name.toLowerCase().includes(q) || i.prompt.toLowerCase().includes(q));
  }, [items, query]);

  const copy = async (key: string, text: string) => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        // The Clipboard API needs a secure context (HTTPS, or localhost) -
        // a typical homelab setup reached over plain http://<lan-ip> doesn't
        // qualify, and navigator.clipboard is undefined there entirely.
        // Fall back to the older execCommand trick, which still works.
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
      }
      setCopiedKey(key);
      setTimeout(() => setCopiedKey((k) => (k === key ? null : k)), 1500);
    } catch {
      setError("Couldn't copy to the clipboard - your browser may be blocking it on a non-HTTPS connection.");
    }
  };

  const suggestFilter = async (item: { prompt: string; faith?: boolean }): Promise<ContentFilter> => {
    const r = await run(() =>
      api.get<{ suggestion: ContentFilter | null }>(`/api/prompts/suggest-filter?text=${encodeURIComponent(item.prompt)}`),
    );
    if (r?.suggestion) return r.suggestion;
    return item.faith ? "christian" : "any";
  };

  const runPrompt = async (item: { name: string; prompt: string; faith?: boolean }, filterOverride?: ContentFilter) => {
    setActive(item);
    setSongs(null);
    setFilteredOut([]);
    setShort(false);
    setRawResponse(null);
    setCreated(null);
    setPlaylistName(`Occasions/${item.name}`);
    setRunning(true);
    const filter = filterOverride ?? (await suggestFilter(item));
    setContentFilter(filter);
    run(() =>
      api.post<{ songs: Song[]; filtered_out: Song[]; short: boolean; raw_response: unknown }>("/api/prompts/run", {
        prompt: item.prompt,
        content_filter: filter,
      }),
    )
      .then((r) => {
        if (!r) return;
        setRawResponse(r.raw_response);
        setSongs(r.songs ?? []);
        setFilteredOut(r.filtered_out ?? []);
        setShort(!!r.short);
      })
      .finally(() => setRunning(false));
  };

  const createPlaylist = () => {
    if (!songs || !playlistName) return;
    const ids = songs.map(songId).filter((x): x is string => !!x);
    run(() => api.post("/api/prompts/create-playlist", { playlist_name: playlistName, item_ids: ids })).then(
      () => setCreated(playlistName),
    );
  };

  return (
    <div>
      <h2>Prompts library</h2>
      <ErrorBanner message={error} />

      <div className="row">
        <button className={tab === "prompts" ? "primary" : ""} onClick={() => setTab("prompts")}>
          Apple playlist prompts
        </button>
        <button className={tab === "recipes" ? "primary" : ""} onClick={() => setTab("recipes")}>
          Playlist recipes
        </button>
        <input
          type="text"
          placeholder="Search…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ marginLeft: "auto", minWidth: 220 }}
        />
      </div>

      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Prompt</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 200).map((item) => (
              <tr key={item.name}>
                <td>{item.name}</td>
                <td className="muted" style={{ maxWidth: 480 }}>
                  {item.prompt}
                </td>
                <td style={{ whiteSpace: "nowrap" }}>
                  <button onClick={() => copy(item.name, item.prompt)}>Copy</button>{" "}
                  {copiedKey === item.name && <span className="chip good">Copied!</span>}{" "}
                  <button onClick={() => runPrompt(item)}>Run in AudioMuse</button>{" "}
                  <button onClick={() => navigate("/playlist-studio", { state: { seedPrompt: item.prompt } })}>
                    Refine in Studio
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length > 200 && <p className="muted">Showing first 200 of {filtered.length} matches.</p>}
      </div>

      <Drawer open={!!active} onClose={() => setActive(null)}>
        {active && (
          <>
            <div className="row" style={{ justifyContent: "space-between", flexWrap: "nowrap" }}>
              <h3 style={{ marginTop: 0 }}>{active.name}</h3>
              <button onClick={() => setActive(null)}>✕</button>
            </div>
            <p className="muted">{active.prompt}</p>
            <div className="row">
              <label style={{ flex: 1 }}>
                Content
                <select
                  value={contentFilter}
                  onChange={(e) => setContentFilter(e.target.value as ContentFilter)}
                >
                  {(Object.keys(CONTENT_FILTER_LABELS) as ContentFilter[]).map((cf) => (
                    <option key={cf} value={cf}>
                      {CONTENT_FILTER_LABELS[cf]}
                    </option>
                  ))}
                </select>
              </label>
              <button disabled={running} onClick={() => runPrompt(active, contentFilter)}>
                {running ? "Running…" : "Run again"}
              </button>
            </div>
            {songs && (
              <>
                <p>{songs.length} songs returned.</p>
                {filteredOut.length > 0 && (
                  <details>
                    <summary className="muted" style={{ cursor: "pointer" }}>
                      Filtered out: {filteredOut.length} track{filteredOut.length === 1 ? "" : "s"}
                    </summary>
                    <ul>
                      {filteredOut.slice(0, 50).map((s, i) => (
                        <li key={songId(s) ?? i}>{songLabel(s)}</li>
                      ))}
                    </ul>
                  </details>
                )}
                {short && (
                  <p className="chip warn">
                    Only {songs.length} tracks matched the {CONTENT_FILTER_LABELS[contentFilter]} filter.
                  </p>
                )}
                {songs.length === 0 && (
                  <>
                    <p className="chip warn">
                      AudioMuse returned a response, but no songs came out of it - either it genuinely found no
                      matches, or this app guessed the wrong field name for the song list. The raw response below
                      settles which.
                    </p>
                    <details>
                      <summary className="muted" style={{ cursor: "pointer" }}>
                        Show raw AudioMuse response
                      </summary>
                      <pre className="log" style={{ marginTop: 8 }}>
                        {JSON.stringify(rawResponse, null, 2)}
                      </pre>
                    </details>
                  </>
                )}
                <ul>
                  {songs.slice(0, 50).map((s, i) => (
                    <li key={songId(s) ?? i}>{songLabel(s)}</li>
                  ))}
                </ul>
                {songs.length > 0 && (
                  <div className="row">
                    <label style={{ flex: 1 }}>
                      Playlist name
                      <input type="text" value={playlistName} onChange={(e) => setPlaylistName(e.target.value)} />
                    </label>
                    <button className="primary" onClick={createPlaylist}>
                      Create playlist
                    </button>
                  </div>
                )}
                {created && <p className="chip good">Created "{created}"</p>}
              </>
            )}
          </>
        )}
      </Drawer>
    </div>
  );
}
