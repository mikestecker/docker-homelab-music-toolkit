"""AudioMuse-AI API client.

Confirmed facts (from AudioMuse's source, Oct 2026 - re-check against
/apidocs/ if these ever 404):
  POST /chat/api/chatPlaylist   {"userInput": "<prompt>"} -> Instant Playlist songs
  POST /chat/api/create_playlist  {"playlist_name": ..., "item_ids": [...]} -> creates it
  GET  /api/search_tracks  {search_query, end} -> [{item_id, title, author, album}]
  POST /api/alchemy  {"items": [{id, op, type}], n, temperature} -> a Song Alchemy blend
Request schemas for all of these are confirmed against a live instance's own
OpenAPI spec (claudedocs/audiomuse-spec.json) - re-fetch
<AUDIOMUSE_URL>/apispec_1.json if any of this ever drifts.

chatPlaylist's real response shape, confirmed from a live response captured
against a real instance (Oct 2026) after the original "top-level songs list"
guess turned out wrong: everything is wrapped in a "response" envelope full
of debug/trace fields (ai_model_selected, executed_query, a verbose "message"
trace, etc.) - the actual song list is at response.query_results, each item
keyed item_id/title/artist/album, not a top-level "songs" key. chat_playlist()
unwraps this into a flat {"songs": [...], "raw_response": <original>} so
every caller gets a stable shape regardless of what AudioMuse's envelope
looks like, and raw_response stays available for debugging if it ever
changes again.

/api/alchemy's RESPONSE shape is, unlike everything above, not documented
anywhere - the spec gives only "each row contains the song and its centroid
for save-as-anchor", no schema. alchemy() below parses it defensively,
inferred from sibling endpoints in the same API that *are* fully documented
(CLAP search, lyrics search, and Hyperbolic Explorer's /similar all return
{"results": [{"item_id", "title", "author", ...}]} - "author" for the artist
name, not "artist", consistently across every one of those) rather than
guessed blind - but it's still an inference, not a confirmed fact, so
raw_response is kept here too in case a live capture ever proves it wrong.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

from app.core.config import AUDIOMUSE_API_TOKEN, AUDIOMUSE_URL


class AudioMuseError(RuntimeError):
    pass


def _post(path, payload, timeout=60):
    if not AUDIOMUSE_URL:
        raise AudioMuseError("AUDIOMUSE_URL isn't set.")
    req = urllib.request.Request(
        f"{AUDIOMUSE_URL}{path}", method="POST",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {AUDIOMUSE_API_TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise AudioMuseError(f"AudioMuse returned {e.code} for {path}: {detail[:300]}")
    except (urllib.error.URLError, OSError) as e:
        raise AudioMuseError(f"AudioMuse at {AUDIOMUSE_URL} is unreachable: {e}")


def _get(path, params=None, timeout=60):
    if not AUDIOMUSE_URL:
        raise AudioMuseError("AUDIOMUSE_URL isn't set.")
    qs = f"?{urllib.parse.urlencode(params)}" if params else ""
    req = urllib.request.Request(
        f"{AUDIOMUSE_URL}{path}{qs}",
        headers={"Authorization": f"Bearer {AUDIOMUSE_API_TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise AudioMuseError(f"AudioMuse returned {e.code} for {path}: {detail[:300]}")
    except (urllib.error.URLError, OSError) as e:
        raise AudioMuseError(f"AudioMuse at {AUDIOMUSE_URL} is unreachable: {e}")


def chat_playlist(user_input):
    """Run Instant Playlist. Max 200 songs; a size in the prompt overrides the
    Number of songs setting; seed songs are left out of the results; results
    are reordered by tempo, energy and key (see the playbook).

    Returns {"songs": [{"id", "title", "artist", "album"}...], "raw_response": ...} -
    see the module docstring for why this unwraps AudioMuse's real envelope
    shape instead of returning it as-is."""
    raw = _post("/chat/api/chatPlaylist", {"userInput": user_input})
    results = (raw.get("response") or {}).get("query_results") or []
    songs = [{"id": str(s["item_id"]), "title": str(s.get("title") or ""),
              "artist": str(s.get("artist") or ""), "album": str(s.get("album") or "")}
             for s in results if s.get("item_id")]
    return {"songs": songs, "raw_response": raw}


def create_playlist(playlist_name, item_ids):
    return _post("/chat/api/create_playlist",
                  {"playlist_name": playlist_name, "item_ids": item_ids})


def search_tracks(query, count=20):
    """GET /api/search_tracks - AudioMuse's own track autocomplete. Confirmed
    response: a bare array of {item_id, title, author, album} (no wrapper
    key - unlike most of this module, this one *is* fully documented)."""
    data = _get("/api/search_tracks", {"search_query": query, "end": count})
    return [{"id": str(s["item_id"]), "title": str(s.get("title") or ""),
              "artist": str(s.get("author") or ""), "album": str(s.get("album") or "")}
            for s in (data or []) if s.get("item_id")]


def _extract_alchemy_results(raw):
    """The response wrapper key isn't confirmed - try the documented sibling
    convention first ("results"), then the chatPlaylist-style "songs", then
    fall back to a bare list response."""
    if isinstance(raw, list):
        return raw
    if not isinstance(raw, dict):
        return []
    return raw.get("results") or raw.get("songs") or []


def alchemy(items, n=None, temperature=None, subtract_distance=None):
    """POST /api/alchemy. `items`: [{"id", "op": "ADD"|"SUBTRACT",
    "type": "song"|"artist"|"anchor"|"mood"|"playlist"}], at least one ADD
    required. Returns {"songs": [...], "raw_response": ...} - see the module
    docstring for why the response parsing here is an inference, not a
    confirmed fact."""
    payload = {"items": items}
    if n is not None:
        payload["n"] = n
    if temperature is not None:
        payload["temperature"] = temperature
    if subtract_distance is not None:
        payload["subtract_distance"] = subtract_distance
    raw = _post("/api/alchemy", payload)
    results = _extract_alchemy_results(raw)
    songs = []
    for s in (results or []):
        sid = s.get("item_id") or s.get("id")
        if not sid:
            continue
        songs.append({"id": str(sid), "title": str(s.get("title") or ""),
                      "artist": str(s.get("author") or s.get("artist") or ""),
                      "album": str(s.get("album") or "")})
    return {"songs": songs, "raw_response": raw}


def reachable(timeout=5):
    """Best-effort reachability for the status page. AudioMuse has no
    documented health endpoint, so this just checks the server answers."""
    try:
        req = urllib.request.Request(f"{AUDIOMUSE_URL}/apidocs/")
        urllib.request.urlopen(req, timeout=timeout)
        return True
    except Exception:
        return False
