"""Playlist folders: file Navidrome playlists into folders by renaming them,
ported from rename-playlists.py. The map file stays the source of truth -
the UI's "assign a folder" action upserts a rule into the same map text this
module reads, it doesn't rename anything by itself.
"""
import os
import uuid

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


# --- Folder tree: a persisted, nestable, droppable-anywhere structure for the
# web UI's drag-and-drop view. Independent of the map file/run() above (that
# stays as the scripted bulk-rename path); this renames in Navidrome
# immediately on every move, keyed by the playlist's stable id rather than
# its name since the name changes on every move. -----------------------------

def _tree_file():
    return os.path.join(cfg.CONFIG_DIR, "playlist-folders-tree.json")


def _empty_tree():
    return {"folders": [], "assignments": {}}


def load_tree():
    return store.load_json(_tree_file(), _empty_tree())


def save_tree(data):
    store.save_json(_tree_file(), data)


def _tree_from_playlist_names(playlists):
    """Auto-create a folder chain per distinct '/'-prefix among current
    playlist names, and assign each playlist to its deepest segment. This is
    the migration path from the old rename-only folders, and what the
    Resync action rebuilds from."""
    folders = []
    folder_id_by_path = {}

    def ensure_folder(path_parts):
        if not path_parts:
            return None
        key = tuple(path_parts)
        if key in folder_id_by_path:
            return folder_id_by_path[key]
        parent_id = ensure_folder(path_parts[:-1])
        fid = uuid.uuid4().hex
        folders.append({"id": fid, "name": path_parts[-1], "parent_id": parent_id})
        folder_id_by_path[key] = fid
        return fid

    assignments = {}
    for p in playlists:
        parts = p["name"].split("/")
        if len(parts) > 1:
            assignments[p["id"]] = ensure_folder(parts[:-1])
    return {"folders": folders, "assignments": assignments}


def ensure_tree_seeded():
    if os.path.exists(_tree_file()):
        return
    try:
        playlists = nd.get_playlists(client="playlist-folders")
    except NavidromeError:
        save_tree(_empty_tree())
        return
    save_tree(_tree_from_playlist_names(playlists))


def resync_tree():
    """Rebuild folders+assignments from current Navidrome playlist names,
    overwriting whatever local tree exists - a manual recovery/migration
    action, not just the first-boot seed."""
    try:
        playlists = nd.get_playlists(client="playlist-folders")
    except NavidromeError as e:
        return {"folders": [], "playlists": [], "error": str(e)}
    save_tree(_tree_from_playlist_names(playlists))
    return get_tree()


def get_tree():
    ensure_tree_seeded()
    try:
        playlists = nd.get_playlists(client="playlist-folders")
    except NavidromeError as e:
        return {"folders": [], "playlists": [], "error": str(e)}
    tree = load_tree()
    assignments = tree["assignments"]
    out_playlists = []
    for p in sorted(playlists, key=lambda p: p["name"].lower()):
        out_playlists.append({
            "id": p["id"], "name": p["name"], "leaf_name": p["name"].rsplit("/", 1)[-1],
            "owner": p.get("owner"), "folder_id": assignments.get(p["id"]),
        })
    return {"folders": tree["folders"], "playlists": out_playlists, "error": None}


def _folders_by_id(folders):
    return {f["id"]: f for f in folders}


def _folder_path(folder_id, folders_by_id):
    """Full '/'-joined path for a folder id, '' for root (None)."""
    parts = []
    fid, seen = folder_id, set()
    while fid is not None and fid in folders_by_id and fid not in seen:
        seen.add(fid)
        f = folders_by_id[fid]
        parts.append(f["name"])
        fid = f["parent_id"]
    return "/".join(reversed(parts))


def _chain_contains(start_id, target_id, folders_by_id):
    """Walking start_id's parent chain (including start_id itself), do we
    ever hit target_id? Used both for move_folder's cycle check (is the new
    parent folder_id itself or one of its descendants?) and for cascade's
    subtree membership check (is this playlist's folder under the root
    being cascaded?)."""
    fid, seen = start_id, set()
    while fid is not None and fid not in seen:
        if fid == target_id:
            return True
        seen.add(fid)
        fid = folders_by_id.get(fid, {}).get("parent_id")
    return False


def _rename_playlist_for_folder(playlist, folder_id, folders_by_id, taken):
    """-> (ok, new_name_or_None, error_or_None). taken is the set of
    lower-cased names currently in use; updated in place on success, same
    collision bookkeeping as run()'s taken set."""
    path = _folder_path(folder_id, folders_by_id)
    leaf = playlist["name"].rsplit("/", 1)[-1]
    new_name = f"{path}/{leaf}" if path else leaf
    if new_name == playlist["name"]:
        return True, new_name, None
    if new_name.lower() in taken:
        return False, None, f"a playlist named '{new_name}' already exists"
    try:
        nd.update_playlist(playlist["id"], name=new_name, client="playlist-folders")
    except NavidromeError as e:
        return False, None, str(e)
    taken.discard(playlist["name"].lower())
    taken.add(new_name.lower())
    return True, new_name, None


def _cascade_rename_subtree(root_folder_id, tree):
    """Rename every playlist assigned at or under root_folder_id to match
    its freshly-computed path. root_folder_id of None means "everywhere"
    (used after a delete that reparents onto root) - harmless for playlists
    outside the affected area since their computed name won't have changed."""
    folders_by_id = _folders_by_id(tree["folders"])
    try:
        playlists = nd.get_playlists(client="playlist-folders")
    except NavidromeError as e:
        return [{"old_name": None, "new_name": None, "ok": False, "error": str(e)}]
    by_id = {p["id"]: p for p in playlists}
    taken = {p["name"].lower() for p in playlists}
    results = []
    for playlist_id, folder_id in tree["assignments"].items():
        if root_folder_id is not None and not _chain_contains(folder_id, root_folder_id, folders_by_id):
            continue
        playlist = by_id.get(playlist_id)
        if playlist is None:
            continue
        old_name = playlist["name"]
        ok, new_name, error = _rename_playlist_for_folder(playlist, folder_id, folders_by_id, taken)
        if ok and new_name == old_name:
            continue  # unchanged, not worth reporting
        results.append({"old_name": old_name, "new_name": new_name, "ok": ok, "error": error})
    return results


def create_folder(name, parent_id=None):
    tree = load_tree()
    folders_by_id = _folders_by_id(tree["folders"])
    if parent_id is not None and parent_id not in folders_by_id:
        raise KeyError(parent_id)
    folder = {"id": uuid.uuid4().hex, "name": name.strip(), "parent_id": parent_id}
    tree["folders"].append(folder)
    save_tree(tree)
    return folder


def rename_folder(folder_id, name):
    tree = load_tree()
    folders_by_id = _folders_by_id(tree["folders"])
    if folder_id not in folders_by_id:
        raise KeyError(folder_id)
    folders_by_id[folder_id]["name"] = name.strip()
    save_tree(tree)
    return {"folder": folders_by_id[folder_id], "renames": _cascade_rename_subtree(folder_id, tree)}


def move_folder(folder_id, parent_id):
    tree = load_tree()
    folders_by_id = _folders_by_id(tree["folders"])
    if folder_id not in folders_by_id:
        raise KeyError(folder_id)
    if parent_id is not None:
        if parent_id not in folders_by_id:
            raise KeyError(parent_id)
        if _chain_contains(parent_id, folder_id, folders_by_id):
            raise ValueError("Can't move a folder into itself or one of its own subfolders.")
    folders_by_id[folder_id]["parent_id"] = parent_id
    save_tree(tree)
    return {"folder": folders_by_id[folder_id], "renames": _cascade_rename_subtree(folder_id, tree)}


def delete_folder(folder_id):
    """Spotify-style delete: the folder's direct child folders and playlists
    are reparented up to its own parent, not destroyed."""
    tree = load_tree()
    folders_by_id = _folders_by_id(tree["folders"])
    if folder_id not in folders_by_id:
        raise KeyError(folder_id)
    parent_id = folders_by_id[folder_id]["parent_id"]
    for f in tree["folders"]:
        if f["parent_id"] == folder_id:
            f["parent_id"] = parent_id
    for pid, fid in tree["assignments"].items():
        if fid == folder_id:
            tree["assignments"][pid] = parent_id
    tree["folders"] = [f for f in tree["folders"] if f["id"] != folder_id]
    save_tree(tree)
    return {"renames": _cascade_rename_subtree(parent_id, tree)}


def move_playlist(playlist_id, folder_id):
    tree = load_tree()
    folders_by_id = _folders_by_id(tree["folders"])
    if folder_id is not None and folder_id not in folders_by_id:
        raise KeyError(folder_id)
    try:
        playlists = nd.get_playlists(client="playlist-folders")
    except NavidromeError as e:
        return {"ok": False, "new_name": None, "error": str(e)}
    playlist = next((p for p in playlists if p["id"] == playlist_id), None)
    if playlist is None:
        return {"ok": False, "new_name": None, "error": f"No such playlist: {playlist_id}"}
    taken = {p["name"].lower() for p in playlists}
    ok, new_name, error = _rename_playlist_for_folder(playlist, folder_id, folders_by_id, taken)
    if ok:
        if folder_id is None:
            tree["assignments"].pop(playlist_id, None)
        else:
            tree["assignments"][playlist_id] = folder_id
        save_tree(tree)
    return {"ok": ok, "new_name": new_name, "error": error}
