"""Playlist Studio: an interactive workshop on top of AudioMuse, for building
a playlist iteratively instead of one-shot "Run in AudioMuse" (that flow
stays in prompts_library, unchanged).

Two ways in:
  - Instant: a free-text prompt, same as prompts_library's "Run in AudioMuse".
  - Alchemy: pick anchor tracks (Include) and optional Exclude tracks from
    your own library, blended via AudioMuse's real POST /api/alchemy -
    confirmed live from the running instance's OpenAPI spec (claudedocs/
    audiomuse-spec.json), after an earlier version of this module worked
    around a genuinely undocumented endpoint by composing an Instant
    Playlist sentence instead. The request schema is fully documented; the
    *response* schema is not (the spec gives only a one-line description -
    "each row contains the song and its centroid"), so audiomuse_client.alchemy()
    parses it defensively and always keeps the raw response available, the
    same safety net that let a real chatPlaylist response-shape bug get
    fixed from one example instead of guessed at twice.
  - Anchor search uses AudioMuse's own /api/search_tracks, not Navidrome's -
    Alchemy's items need AudioMuse's own item_id space (confirmed distinct
    from Navidrome's Subsonic ids), so anchors are sourced from the same
    system Alchemy will actually query.

Every generation (instant, alchemy, or a refine) is saved to a per-session
history so refine() can diff against "whatever we showed the user last" and
so a session's attempts can be browsed without regenerating. Sessions live
under CONFIG_DIR/playlist-studio/<session_id>/manifest.json - same shape as
playlist_covers' per-playlist history, minus an image file: the track list
itself is the artifact here, stored directly in the manifest.
"""
import os
import time
import uuid

from app.core import config as cfg
from app.core import store
from app.core.audiomuse_client import alchemy, chat_playlist, create_playlist, search_tracks


def _studio_dir(session_id):
    return os.path.join(cfg.CONFIG_DIR, "playlist-studio", session_id)


def _manifest_path(session_id):
    return os.path.join(_studio_dir(session_id), "manifest.json")


def search_anchors(query):
    """Candidate Include/Exclude tracks for Alchemy mode."""
    if not query or not query.strip():
        return []
    return search_tracks(query.strip())


# Alchemy's "temperature" is documented as a softmax sampling temperature
# (higher = more varied/surprising, lower = tighter/more predictable) - this
# maps the UI's 3-state control onto it. ALCHEMY_DEFAULT_TEMPERATURE (server
# default) is what "balanced" leaves in effect by sending 1.0, a reasonable
# middle value, not a guess at the server's own default.
VARIETY_TEMPERATURE = {"tight": 0.3, "balanced": 1.0, "wide": 2.0}


def _tracks_prompt(tracks, limit=8):
    names = []
    for t in tracks[:limit]:
        title, artist = (t.get("title") or "").strip(), (t.get("artist") or "").strip()
        label = f"{title} by {artist}" if title and artist else title or artist
        if label:
            names.append(label)
    return ", ".join(names)


def _save_history(session_id, kind, tracks, detail):
    directory = _studio_dir(session_id)
    os.makedirs(directory, exist_ok=True)
    entry_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    manifest = store.load_json(_manifest_path(session_id), [])
    entry = {"id": entry_id, "created": time.time(), "kind": kind, "tracks": tracks, **detail}
    manifest.insert(0, entry)
    store.save_json(_manifest_path(session_id), manifest[:50])
    return entry


def history(session_id):
    return store.load_json(_manifest_path(session_id), [])


def _latest_entry(session_id):
    h = history(session_id)
    if not h:
        raise ValueError("No generation history for this session yet.")
    return h[0]


def generate_instant(prompt, session_id=None):
    session_id = session_id or uuid.uuid4().hex
    raw = chat_playlist(prompt)
    tracks = raw["songs"]
    entry = _save_history(session_id, "instant", tracks, {"prompt": prompt})
    return session_id, entry


def generate_alchemy(anchors, excludes, size, variety="balanced", session_id=None):
    session_id = session_id or uuid.uuid4().hex
    if not anchors:
        raise ValueError("Alchemy needs at least one anchor track.")
    items = [{"id": a["id"], "op": "ADD", "type": "song"} for a in anchors]
    items += [{"id": e["id"], "op": "SUBTRACT", "type": "song"} for e in excludes]
    raw = alchemy(items, n=size, temperature=VARIETY_TEMPERATURE.get(variety, 1.0))
    tracks = raw["songs"]
    entry = _save_history(session_id, "alchemy", tracks,
                           {"anchors": anchors, "excludes": excludes, "variety": variety})
    return session_id, entry


def refine(session_id, instruction):
    """Builds a fresh "like these songs, but: <instruction>" prompt from
    whatever the session's current track list is, so it works the same way
    regardless of whether that list came from Instant or Alchemy (those two
    modes no longer share a common "prompt" field to reuse), and so repeated
    refinements don't chain onto an ever-growing prompt string."""
    prev = _latest_entry(session_id)
    instruction = instruction.strip()
    if not instruction:
        raise ValueError("Describe what to change.")
    tracks = prev.get("tracks") or []
    if not tracks:
        raise ValueError("This session's last entry has no tracks to refine from.")
    seed = _tracks_prompt(tracks)
    combined = f"Songs like {seed}. Also: {instruction}" if seed else instruction
    raw = chat_playlist(combined)
    new_tracks = raw["songs"]
    entry = _save_history(session_id, "refine", new_tracks, {"prompt": combined, "instruction": instruction})
    return entry, diff_tracks(tracks, new_tracks)


def _lis_indices(seq):
    """Positions (into seq) of one longest increasing subsequence. O(n^2),
    fine at these sizes (<=200 tracks) - simple and easy to verify over a
    clever O(n log n) version."""
    n = len(seq)
    if n == 0:
        return set()
    lengths = [1] * n
    prev = [-1] * n
    for i in range(n):
        for j in range(i):
            if seq[j] < seq[i] and lengths[j] + 1 > lengths[i]:
                lengths[i] = lengths[j] + 1
                prev[i] = j
    best = max(range(n), key=lambda i: lengths[i])
    result = set()
    while best != -1:
        result.add(best)
        best = prev[best]
    return result


def diff_tracks(old, new):
    """Added/removed/kept/moved between two track lists, matched by id.
    "moved" is the subset of kept tracks whose relative order changed -
    found via the longest run of kept tracks that stayed in the same
    relative order (an LIS over their old-list positions); everything not
    in that run moved relative to it."""
    old_by_id = {t["id"]: t for t in old if t.get("id")}
    new_by_id = {t["id"]: t for t in new if t.get("id")}
    added = [t for t in new if not t.get("id") or t["id"] not in old_by_id]
    removed = [t for t in old if not t.get("id") or t["id"] not in new_by_id]
    kept_ids = [t["id"] for t in new if t.get("id") and t["id"] in old_by_id]
    old_index = {t["id"]: i for i, t in enumerate(old) if t.get("id")}
    old_positions = [old_index[tid] for tid in kept_ids]
    lis = _lis_indices(old_positions)
    kept = [new_by_id[tid] for tid in kept_ids]
    moved = [new_by_id[kept_ids[i]] for i in range(len(kept_ids)) if i not in lis]
    return {"added": added, "removed": removed, "kept": kept, "moved": moved}


def create_playlist_from_session(session_id, entry_id, playlist_name):
    entry = next((e for e in history(session_id) if e["id"] == entry_id), None)
    if entry is None:
        raise ValueError("No such history entry for this session.")
    ids = [t["id"] for t in entry["tracks"] if t.get("id")]
    if not ids:
        raise ValueError("This entry has no tracks with usable ids.")
    return create_playlist(playlist_name, ids)
