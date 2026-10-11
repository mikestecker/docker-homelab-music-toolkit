"""Playlist Studio: an interactive workshop on top of AudioMuse's Instant
Playlist, for building a playlist iteratively instead of one-shot "Run in
AudioMuse" (that flow stays in prompts_library, unchanged).

Two ways in:
  - Instant: a free-text prompt, same as prompts_library's "Run in AudioMuse".
  - Alchemy: pick anchor tracks (Include) and optional Exclude tracks from
    your own library, searched via Navidrome. AudioMuse has no confirmed
    JSON API for its own Song Alchemy feature (its web UI only - see
    docs/playbook/0-AudioMuse-Playbook.md, which never states an API path
    for it, and app.core.audiomuse_client's own header comment flags this as
    unconfirmed). Rather than guess an unverified endpoint, Alchemy mode here
    composes a multi-seed Instant Playlist sentence from the chosen anchors'
    artists ("Songs like X, Y, Z...") and calls the one confirmed, working
    endpoint - chatPlaylist already blends multiple named seeds itself (the
    playbook's own example: "like Tom Petty and The Killers but more
    upbeat"), so this leans on real, confirmed behavior rather than
    reimplementing a cruder merge ourselves. If a real /api/alchemy contract
    is confirmed later, only generate_alchemy()'s body needs to change.

Every song dict here comes straight from audiomuse_client.chat_playlist(),
which already normalizes AudioMuse's real (envelope-wrapped) response into
a flat {"id", "title", "artist", "album"} shape - no second normalization
layer here, so there's exactly one place that knows AudioMuse's real
response shape instead of two that could quietly drift apart.

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
from app.core import navidrome_client as nd
from app.core import store
from app.core.audiomuse_client import chat_playlist, create_playlist


def _studio_dir(session_id):
    return os.path.join(cfg.CONFIG_DIR, "playlist-studio", session_id)


def _manifest_path(session_id):
    return os.path.join(_studio_dir(session_id), "manifest.json")


def search_anchors(query):
    """Candidate Include/Exclude tracks for Alchemy mode, from the real
    library via Navidrome's own search - unlike AudioMuse's response shape,
    Subsonic's id/title/artist fields are well-known, no guessing needed."""
    if not query or not query.strip():
        return []
    songs = nd.search_songs(query.strip())
    return [{"id": str(s["id"]), "title": s.get("title", ""), "artist": s.get("artist", "")}
            for s in songs if s.get("id")]


def _unique_artists(tracks):
    seen = []
    for t in tracks:
        artist = (t.get("artist") or "").strip()
        if artist and artist not in seen:
            seen.append(artist)
    return seen


VARIETY_PHRASES = {
    "tight": "close, predictable matches to these artists",
    "balanced": None,
    "wide": "more unexpected and varied picks, don't just pick the obvious hits",
}


def _alchemy_prompt(anchors, excludes, size, variety):
    anchor_artists = _unique_artists(anchors)
    if not anchor_artists:
        raise ValueError("Alchemy needs at least one anchor track.")
    parts = [f"Songs like {', '.join(anchor_artists)}"]
    exclude_artists = _unique_artists(excludes)
    if exclude_artists:
        parts.append(f"nothing like {', '.join(exclude_artists)}")
    phrase = VARIETY_PHRASES.get(variety)
    if phrase:
        parts.append(phrase)
    if size:
        parts.append(f"{size} songs")
    return ", ".join(parts)


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
    prompt = _alchemy_prompt(anchors, excludes, size, variety)
    raw = chat_playlist(prompt)
    tracks = raw["songs"]
    entry = _save_history(session_id, "alchemy", tracks,
                           {"prompt": prompt, "anchors": anchors, "excludes": excludes})
    return session_id, entry


def refine(session_id, instruction):
    prev = _latest_entry(session_id)
    base_prompt = prev.get("prompt")
    if not base_prompt:
        raise ValueError("This session's last entry has no prompt to refine.")
    instruction = instruction.strip()
    if not instruction:
        raise ValueError("Describe what to change.")
    combined = f"{base_prompt}. Also: {instruction}"
    raw = chat_playlist(combined)
    tracks = raw["songs"]
    entry = _save_history(session_id, "refine", tracks,
                           {"prompt": combined, "instruction": instruction})
    return entry, diff_tracks(prev["tracks"], tracks)


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
