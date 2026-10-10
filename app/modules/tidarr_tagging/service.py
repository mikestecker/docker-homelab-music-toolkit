"""Tidarr import filing: mark the playlists Navidrome imported from Tidarr's
.m3u files, ported from tag-tidarr-playlists.py. Same two-step approach as
the original - the native API is the only one that says which file a
playlist came from, so that's used to find the Tidarr imports, then
Subsonic's updatePlaylist renames/tags (or undoes) them.
"""
import os

from app.core import config as cfg
from app.core import navidrome_client as nd
from app.core import store
from app.core.navidrome_client import NavidromeError

DEFAULT_SETTINGS = {"prefix": "Imports/Tidarr/", "path_match": "/m3u/playlist/"}


def _settings_file():
    return os.path.join(cfg.CONFIG_DIR, "tidarr-tagging-settings.json")


def get_settings():
    return dict(DEFAULT_SETTINGS, **store.load_json(_settings_file(), {}))


def save_settings(**kw):
    settings = get_settings()
    settings.update({k: v for k, v in kw.items() if v is not None})
    store.save_json(_settings_file(), settings)
    return settings


def run(dry_run=True, undo=False):
    """-> {dry_run, undo, log, items, changed_count, error}."""
    settings = get_settings()
    prefix, path_match = settings["prefix"], settings["path_match"]
    log = []

    try:
        playlists = nd.native_playlists()
    except NavidromeError as e:
        return {"dry_run": dry_run, "undo": undo, "log": [f"STOP  {e}"],
                "items": [], "changed_count": 0, "error": str(e)}

    tidarr = [p for p in playlists if path_match in (p.get("path") or "")]
    log.append(f"{'' if not dry_run else 'DRY RUN, nothing will change. '}"
               f"{len(tidarr)} of {len(playlists)} playlists came from Tidarr ({path_match}).")

    changed = 0
    items = []
    for p in tidarr:
        name, fname = p["name"], os.path.basename(p["path"])
        tag = f"Tidarr import: {fname}"
        if undo:
            if not name.startswith(prefix):
                continue
            new_name, new_comment = name[len(prefix):], ""
        else:
            if name.startswith(prefix) and (p.get("comment") or "") == tag:
                continue
            new_name = name if name.startswith(prefix) else prefix + name
            new_comment = tag
        log.append(f"  {'RENAME' if not dry_run else 'WOULD '}  {name}  ->  {new_name}")
        changed += 1
        item = {"id": p["id"], "name": name, "new_name": new_name, "fail": None}
        if not dry_run:
            try:
                nd.update_playlist(p["id"], name=new_name, comment=new_comment,
                                    client="tidarr-tagging")
            except NavidromeError as e:
                log.append(f"  FAIL    {name}: {e}")
                item["fail"] = str(e)
        items.append(item)
    log.append(f"Done. {'Changed' if not dry_run else 'Would change'} {changed}.")
    return {"dry_run": dry_run, "undo": undo, "log": log, "items": items,
            "changed_count": changed, "error": None}
