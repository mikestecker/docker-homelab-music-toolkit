"""Cluster cleanup: take stray worship songs out of AudioMuse's clustering
playlists. Ported from clean-clusters.py - same matching rules, same
Subsonic calls, same "remove only if a minority" safety rule. Behavior
unchanged; CFG from cleanup.env becomes settings in /config, DRY_RUN becomes
the `dry_run` argument every caller (API route, scheduled job, CLI) passes
explicitly, and the plain-text log becomes a structured result plus a log
list, so the UI and the scheduler's run history can show exactly what the
script would have printed.
"""
import os

from app.core import config as cfg
from app.core import navidrome_client as nd
from app.core import store
from app.core.artist_matcher import credit_keys
from app.core.config import ND_USER
from app.core.navidrome_client import NavidromeError
from app.modules.christian_artists import service as christian_artists

SUFFIX = "_automatic"
DEFAULT_SETTINGS = {"max_share": 0.34, "min_seconds": 0, "rename_prefix": "",
                     "scope": "christian", "reverse_cleanup": False}


def _settings_file():
    # Computed from cfg.CONFIG_DIR on every call, not frozen at import time -
    # see the module-level comment in christian_artists/service.py for why.
    return os.path.join(cfg.CONFIG_DIR, "cleanup-settings.json")


def get_settings():
    return dict(DEFAULT_SETTINGS, **store.load_json(_settings_file(), {}))


def save_settings(**kw):
    settings = get_settings()
    settings.update({k: v for k, v in kw.items() if v is not None})
    store.save_json(_settings_file(), settings)
    return settings


# ---------- the run itself ----------

def run(dry_run=True):
    """-> {dry_run, log, playlists, total_removed, error}. Mirrors
    clean-clusters.py's main(): same minority rule, same highest-index-first
    removal order, same rename-then-clean sequencing. The listed-artist set
    now comes from the Christian artists store (scoped to "christian" or
    "worship"), not a flat text file - see app.modules.christian_artists."""
    settings = get_settings()
    max_share = float(settings["max_share"])
    min_seconds = int(settings["min_seconds"])
    rename_prefix = settings["rename_prefix"] or ""
    scope = settings.get("scope") or "christian"
    reverse_cleanup = bool(settings.get("reverse_cleanup"))

    log = []

    def record(msg):
        log.append(msg)

    try:
        artists = christian_artists.scoped_name_keys(scope)
    except OSError as e:
        return {"dry_run": dry_run, "log": [f"STOP  can't read the Christian artists list: {e}"],
                "playlists": [], "total_removed": 0, "error": str(e)}

    record(f"{'DRY RUN, nothing will change. ' if dry_run else ''}"
           f"{len(artists)} listed artists (scope: {scope}), remove when they're at most "
           f"{max_share:.0%} of a playlist"
           + (f", also dropping tracks under {min_seconds}s" if min_seconds else "")
           + (", reverse cleanup on (removes the secular minority of a mostly-listed cluster)"
              if reverse_cleanup else ""))

    try:
        nd.ping(client="cluster-cleanup")
        playlists = nd.get_playlists(client="cluster-cleanup")
    except NavidromeError as e:
        record(f"STOP  {e}")
        return {"dry_run": dry_run, "log": log, "playlists": [], "total_removed": 0, "error": str(e)}

    clusters = [p for p in playlists if p.get("name", "").endswith(SUFFIX)]
    record(f"Found {len(clusters)} clustering playlists")
    total_removed = 0
    out_playlists = []

    for p in clusters:
        name, pid = p["name"], p["id"]
        entry = {"name": name, "id": pid, "owner": p.get("owner"), "owner_skipped": False,
                  "total_songs": 0, "worship_removed": 0, "short_removed": 0, "secular_removed": 0,
                  "kept_worship_leaning": False, "worship_share": 0.0,
                  "renamed_to": None, "removed_tracks": [], "error": None}
        if p.get("owner") and p["owner"] != ND_USER:
            record(f"SKIP  {name}: owned by {p['owner']}, not the configured Navidrome user. "
                   "Only the owner can edit it.")
            entry["owner_skipped"] = True
            out_playlists.append(entry)
            continue
        try:
            songs = nd.get_playlist_entries(pid, client="cluster-cleanup")
        except NavidromeError as e:
            entry["error"] = str(e)
            out_playlists.append(entry)
            continue
        if not songs:
            out_playlists.append(entry)
            continue
        entry["total_songs"] = len(songs)

        scoped = [i for i, s in enumerate(songs) if credit_keys(s.get("artist")) & artists]
        share = len(scoped) / len(songs)
        entry["worship_share"] = share

        remove_scoped, remove_secular = [], []
        if scoped and share > max_share:
            record(f"KEEP  {name}: {len(scoped)}/{len(songs)} songs ({share:.0%}) are listed "
                   "artists, so this is a worship-leaning cluster")
            entry["kept_worship_leaning"] = True
            if reverse_cleanup and share >= (1 - max_share):
                remove_secular = [i for i in range(len(songs)) if i not in set(scoped)]
                if remove_secular:
                    record(f"REVERSE {name}: {len(remove_secular)}/{len(songs)} songs are the "
                           "secular minority of this mostly-listed cluster")
        elif scoped:
            remove_scoped = scoped

        short = [i for i, s in enumerate(songs)
                 if min_seconds and 0 < int(s.get("duration") or 0) < min_seconds]
        drop = sorted(set(remove_scoped) | set(remove_secular) | set(short), reverse=True)

        if rename_prefix and not name.startswith(rename_prefix):
            new_name = rename_prefix + name
            record(f"{'WOULD' if dry_run else 'NAME '} {name}  ->  {new_name}")
            if not dry_run:
                try:
                    nd.update_playlist(pid, name=new_name, client="cluster-cleanup")
                except NavidromeError as e:
                    record(f"FAIL  renaming {name}: {e}")
            entry["renamed_to"] = new_name
            name = new_name

        if not drop:
            out_playlists.append(entry)
            continue

        record(f"{'WOULD' if dry_run else 'CLEAN'} {name}: remove {len(drop)} of {len(songs)} songs")
        scoped_set, secular_set = set(remove_scoped), set(remove_secular)
        for i in sorted(drop):
            s = songs[i]
            if i in secular_set:
                why, direction = "secular minority", "secular_minority"
            elif i in scoped_set:
                why, direction = "listed artist", "scoped_minority"
            else:
                why, direction = "short", None
            record(f"        - {s.get('title')} / {s.get('artist')}  ({why})")
            entry["removed_tracks"].append({"title": s.get("title"), "artist": s.get("artist"),
                                             "why": why, "direction": direction})
        entry["worship_removed"] = sum(1 for i in drop if i in scoped_set)
        entry["secular_removed"] = sum(1 for i in drop if i in secular_set)
        entry["short_removed"] = sum(1 for i in drop if i not in scoped_set and i not in secular_set)
        total_removed += len(drop)
        out_playlists.append(entry)
        if dry_run:
            continue

        # Remove from the highest index down, one per call, so earlier indexes stay valid.
        for i in drop:
            try:
                nd.update_playlist(pid, song_index_to_remove=i, client="cluster-cleanup")
            except NavidromeError as e:
                record(f"FAIL  removing index {i} from {name}: {e}")
        try:
            after = nd.get_playlist_entries(pid, client="cluster-cleanup")
            if len(after) != len(songs) - len(drop):
                record(f"WARN  {name}: expected {len(songs) - len(drop)} songs after cleanup, "
                       f"found {len(after)}")
        except NavidromeError as e:
            record(f"WARN  couldn't confirm {name} after cleanup: {e}")

    record(f"Done. {'Would remove' if dry_run else 'Removed'} {total_removed} songs.")
    return {"dry_run": dry_run, "log": log, "playlists": out_playlists,
            "total_removed": total_removed, "error": None}
