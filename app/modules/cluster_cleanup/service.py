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
import re

from app.core import config as cfg
from app.core import navidrome_client as nd
from app.core import store
from app.core.config import ND_USER
from app.core.navidrome_client import NavidromeError

SUFFIX = "_automatic"
_DEFAULT_ARTIST_FILE = os.path.join(cfg.CONFIG_DEFAULTS_DIR, "worship-artists.txt")
DEFAULT_SETTINGS = {"max_share": 0.34, "min_seconds": 0, "rename_prefix": ""}


def _artist_file():
    # Computed from cfg.CONFIG_DIR on every call, not frozen at import time,
    # so it tracks CONFIG_DIR even when tests (or a future reconfiguration)
    # change it after this module has already been imported.
    return os.path.join(cfg.CONFIG_DIR, "worship-artists.txt")


def _settings_file():
    return os.path.join(cfg.CONFIG_DIR, "cleanup-settings.json")


def ensure_seeded():
    store.seed_if_missing(_artist_file(), _DEFAULT_ARTIST_FILE)


def get_settings():
    return dict(DEFAULT_SETTINGS, **store.load_json(_settings_file(), {}))


def save_settings(**kw):
    settings = get_settings()
    settings.update({k: v for k, v in kw.items() if v is not None})
    store.save_json(_settings_file(), settings)
    return settings


def get_artists_text():
    ensure_seeded()
    return store.load_text(_artist_file())


def save_artists_text(text):
    store.save_text(_artist_file(), text)


# ---------- artist matching (unchanged from clean-clusters.py) ----------

def norm(name):
    s = (name or "").lower().replace("&", " and ").replace("+", " and ")
    s = re.sub(r"[^\w\s]", " ", s)  # drop punctuation: "Lofi Hymns." == "lofi hymns"
    return re.sub(r"\s+", " ", s).strip()


SPLIT = re.compile(r"\s*(?:,|;|/|\bfeat\.?|\bft\.?|\bfeaturing\b|\bwith\b|\bx\b|&|\band\b)\s*", re.I)


def credit_names(artist):
    """The full credit plus each name in it, normalized."""
    names = {norm(artist)}
    names.update(norm(p) for p in SPLIT.split(artist or "") if p and p.strip())
    names.discard("")
    return names


def load_artists(text):
    out = set()
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.add(norm(line))
    return out


# ---------- the run itself ----------

def run(dry_run=True):
    """-> {dry_run, log, playlists, total_removed, error}. Mirrors
    clean-clusters.py's main(): same minority rule, same highest-index-first
    removal order, same rename-then-clean sequencing."""
    ensure_seeded()
    settings = get_settings()
    max_share = float(settings["max_share"])
    min_seconds = int(settings["min_seconds"])
    rename_prefix = settings["rename_prefix"] or ""

    log = []

    def record(msg):
        log.append(msg)

    try:
        artists = load_artists(get_artists_text())
    except OSError as e:
        return {"dry_run": dry_run, "log": [f"STOP  can't read the worship artist list: {e}"],
                "playlists": [], "total_removed": 0, "error": str(e)}

    record(f"{'DRY RUN, nothing will change. ' if dry_run else ''}"
           f"{len(artists)} listed artists, remove when they're at most {max_share:.0%} of a playlist"
           + (f", also dropping tracks under {min_seconds}s" if min_seconds else ""))

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
                  "total_songs": 0, "worship_removed": 0, "short_removed": 0,
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

        worship = [i for i, s in enumerate(songs) if credit_names(s.get("artist")) & artists]
        share = len(worship) / len(songs)
        entry["worship_share"] = share
        if worship and share > max_share:
            record(f"KEEP  {name}: {len(worship)}/{len(songs)} songs ({share:.0%}) are listed "
                   "artists, so this is a worship-leaning cluster")
            entry["kept_worship_leaning"] = True
            worship = []
        short = [i for i, s in enumerate(songs)
                 if min_seconds and 0 < int(s.get("duration") or 0) < min_seconds]
        drop = sorted(set(worship) | set(short), reverse=True)

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
        for i in sorted(drop):
            s = songs[i]
            why = "short" if i in short and i not in worship else "listed artist"
            record(f"        - {s.get('title')} / {s.get('artist')}  ({why})")
            entry["removed_tracks"].append({"title": s.get("title"), "artist": s.get("artist"), "why": why})
        entry["worship_removed"] = sum(1 for i in drop if i in worship)
        entry["short_removed"] = sum(1 for i in drop if i in short and i not in worship)
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
