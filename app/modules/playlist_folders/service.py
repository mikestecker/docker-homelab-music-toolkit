"""Playlist folders: file Navidrome playlists into folders by renaming them,
ported from rename-playlists.py. The map file stays the source of truth -
the UI's "assign a folder" action upserts a rule into the same map text this
module reads, it doesn't rename anything by itself.
"""
import os

from app.core import config as cfg
from app.core import navidrome_client as nd
from app.core import store
from app.core.config import ND_USER
from app.core.navidrome_client import NavidromeError

_DEFAULT_MAP_FILE = os.path.join(cfg.CONFIG_DEFAULTS_DIR, "playlist-folders.txt")


def _map_file():
    return os.path.join(cfg.CONFIG_DIR, "playlist-folders.txt")


def ensure_seeded():
    store.seed_if_missing(_map_file(), _DEFAULT_MAP_FILE)


def get_map_text():
    ensure_seeded()
    return store.load_text(_map_file())


def save_map_text(text):
    store.save_text(_map_file(), text)


def parse_map(text):
    """-> (exact, prefixes, warnings). Unchanged from rename-playlists.py's
    load_map(), operating on text instead of a file path."""
    exact, prefixes, warnings = {}, [], []
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "=>" not in line:
            warnings.append(f"line {n} has no '=>', skipped: {line}")
            continue
        old, new = line.split("=>", 1)
        if old.strip().lower().startswith("prefix:"):
            prefixes.append((old.split(":", 1)[1].lstrip(), new.lstrip()))
        else:
            exact[old.strip().lower()] = new.strip()
    return exact, prefixes, warnings


def upsert_rule(old_name, new_full_name):
    """Add or replace the exact-match rule for one playlist in the map file."""
    text = get_map_text()
    lines = text.splitlines()
    key = old_name.strip().lower()
    out, replaced = [], False
    for raw in lines:
        line = raw.rstrip("\n")
        if ("=>" in line and not line.lstrip().startswith("#")
                and not line.split("=>", 1)[0].strip().lower().startswith("prefix:")
                and line.split("=>", 1)[0].strip().lower() == key):
            out.append(f"{old_name} => {new_full_name}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(f"{old_name} => {new_full_name}")
    save_map_text("\n".join(out) + "\n")


def list_playlists_by_folder():
    """Every current playlist, grouped by the folder its name implies
    (everything before the last '/'), for the UI's grouped view."""
    try:
        playlists = nd.get_playlists(client="playlist-folders")
    except NavidromeError as e:
        return {"folders": {}, "error": str(e)}
    folders = {}
    for p in sorted(playlists, key=lambda p: p["name"].lower()):
        name = p["name"]
        folder = name.rsplit("/", 1)[0] if "/" in name else ""
        folders.setdefault(folder, []).append({"id": p["id"], "name": name, "owner": p.get("owner")})
    return {"folders": folders, "error": None}


def run(dry_run=True):
    """-> {dry_run, log, items, changed_count, error}. Mirrors
    rename-playlists.py's main(): exact rules first, then prefix rules,
    skipping name collisions and reporting non-owned playlists."""
    log = []
    try:
        playlists = nd.get_playlists(client="playlist-folders")
    except NavidromeError as e:
        return {"dry_run": dry_run, "log": [f"STOP  {e}"], "items": [], "changed_count": 0,
                "error": str(e)}

    exact, prefixes, warnings = parse_map(get_map_text())
    log.extend(f"WARN  {w}" for w in warnings)
    log.append(f"{'' if not dry_run else 'DRY RUN, nothing will change. '}{len(playlists)} playlists, "
               f"{len(exact)} name rules, {len(prefixes)} prefix rules.")

    taken = {p["name"].lower() for p in playlists}
    changed = 0
    items = []
    for p in sorted(playlists, key=lambda p: p["name"].lower()):
        name = p["name"]
        new = exact.get(name.strip().lower())
        if new is None:
            for old_pfx, new_pfx in prefixes:
                if name.startswith(old_pfx) and not name.startswith(new_pfx):
                    new = new_pfx + name[len(old_pfx):]
                    break
        if not new or new == name:
            continue
        if new.lower() in taken:
            log.append(f"  SKIP    {name}  ->  {new}  (a playlist with that name already exists)")
            continue
        item = {"id": p["id"], "name": name, "new_name": new, "owner": p.get("owner"),
                 "not_owned": bool(p.get("owner") and p["owner"] != ND_USER), "fail": None}
        if item["not_owned"]:
            log.append(f"  NOTE    {name} is owned by {p['owner']}; this only works if "
                       f"{ND_USER} is an admin")
        log.append(f"  {'RENAME' if not dry_run else 'WOULD '}  {name}  ->  {new}")
        changed += 1
        if not dry_run:
            try:
                nd.update_playlist(p["id"], name=new, client="playlist-folders")
                taken.discard(name.lower())
                taken.add(new.lower())
            except NavidromeError as e:
                log.append(f"  FAIL    {name}: {e}")
                item["fail"] = str(e)
        items.append(item)
    log.append(f"Done. {'Renamed' if not dry_run else 'Would rename'} {changed}.")
    return {"dry_run": dry_run, "log": log, "items": items, "changed_count": changed, "error": None}
