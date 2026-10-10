"""m3u path fixer: repoint .m3u playlist entries at the files you have now,
ported from fix-m3u-paths.py. Same matching rules (artist folder + track
title, ignoring numbers/extension/edition words), same backup-before-write
behavior. This is the one module besides duplicate_finder that writes to the
music library directly, so writes are contained to the playlist folder with
the same realpath/no-symlink discipline duplicate_finder uses for the whole
library - just scoped to this module's own, much narrower, slice of it.
"""
import os
import re
import shutil
import unicodedata
from collections import defaultdict
from datetime import datetime

from app.core import config as cfg
from app.core import store

AUDIO = {".flac", ".m4a", ".mp3", ".alac", ".aac", ".ogg", ".opus", ".wav",
         ".aiff", ".aif", ".wma", ".dsf"}
EDITION = re.compile(r"\b(deluxe|expanded|edition|remaster(ed)?|anniversary|special|version|"
                     r"bonus|explicit|clean)\b", re.I)

# The host path .m3u files may still reference from before this app ran in
# a container (e.g. a bare host path like /mnt/pool/media/music that predates
# a Docker /music mount). Empty by default - nothing is assumed about any
# particular NAS layout. Set this per-deployment from the UI/API only if your
# existing .m3u files actually contain that style of absolute path; this app
# always writes and reads through cfg.MUSIC_DIR regardless.
DEFAULT_HOST_MUSIC_ROOT = ""


def _settings_file():
    return os.path.join(cfg.CONFIG_DIR, "m3u-fix-settings.json")


def _default_settings():
    return {"playlists_dir": os.path.join(cfg.MUSIC_DIR, "m3u", "playlist"),
            "host_music_root": DEFAULT_HOST_MUSIC_ROOT}


def get_settings():
    return dict(_default_settings(), **store.load_json(_settings_file(), {}))


def _inside(path, root):
    return os.path.commonpath([path, root]) == root


def save_settings(**kw):
    settings = get_settings()
    settings.update({k: v for k, v in kw.items() if v is not None})
    if settings.get("playlists_dir"):
        # Defense in depth: this setting controls where run() walks and
        # writes .m3u files. Without this check, an authenticated session
        # could point it at an arbitrary filesystem path - require it to
        # stay inside the library mount, the same containment duplicate_finder
        # enforces for its own quarantine directory.
        music_root = os.path.realpath(cfg.MUSIC_DIR)
        pl_dir = os.path.realpath(settings["playlists_dir"])
        if not _inside(pl_dir, music_root):
            raise ValueError(f"playlists_dir must be inside the music library ({music_root}), got {pl_dir}")
    store.save_json(_settings_file(), settings)
    return settings


# ---------- matching (unchanged from fix-m3u-paths.py) ----------

def compact(s):
    """Lowercase letters and digits only: 'half·alive' == 'Half Alive'."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower().replace("&", "and"))


def title_key(filename):
    stem = os.path.splitext(os.path.basename(filename))[0]
    stem = re.sub(r"^\s*(\d{1,2}[-.])?\d{1,3}\s*[-._]?\s+", "", stem)
    stem = re.sub(r"\s*[\(\[](feat|ft|with)\.?[^\)\]]*[\)\]]", "", stem, flags=re.I)
    return compact(stem)


def track_no(filename):
    m = re.match(r"^\s*(?:\d{1,2}[-.])?(\d{1,3})\b", os.path.basename(filename))
    return int(m.group(1)) if m else None


def album_key(folder):
    folder = re.sub(r"[\(\[]\s*\d{4}\s*[\)\]]", "", folder)
    folder = re.sub(r"[\(\[][^\)\]]*[\)\]]",
                    lambda m: "" if EDITION.search(m.group(0)) else m.group(0), folder)
    return compact(folder)


def index_library(root, skip):
    idx = defaultdict(list)
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if os.path.join(dirpath, d) not in skip
                       and not d.startswith(".")]
        for f in filenames:
            if os.path.splitext(f)[1].lower() not in AUDIO:
                continue
            rel = os.path.relpath(os.path.join(dirpath, f), root)
            parts = rel.split(os.sep)
            artist = compact(parts[0]) if len(parts) > 1 else ""
            album = album_key(parts[-2]) if len(parts) > 2 else ""
            idx[title_key(f)].append((rel, artist, album, track_no(f)))
            count += 1
    return idx, count


def find_match(old_rel, idx):
    parts = old_rel.replace("\\", "/").split("/")
    artist = compact(parts[0]) if len(parts) > 1 else ""
    album = album_key(parts[-2]) if len(parts) > 2 else ""
    tkey, tno = title_key(parts[-1]), track_no(parts[-1])
    cands = [c for c in idx.get(tkey, []) if not artist or c[1] == artist]
    if not cands and artist:
        allc = idx.get(tkey, [])
        if len(allc) == 1:
            return allc[0][0], "title only (artist folder differs)"
        return None, "not in library" if not allc else f"{len(allc)} songs with that title, none under this artist"
    if not cands:
        return None, "not in library"

    def score(c):
        return ((c[2] == album) * 4 + (bool(album) and (album in c[2] or c[2] in album)) * 2
                + (tno is not None and c[3] == tno) + c[0].lower().endswith(".flac") * 0.5)
    cands.sort(key=lambda c: (-score(c), len(c[0])))
    note = "exact album" if cands[0][2] == album else "other edition/album"
    return cands[0][0], note


# ---------- safety: writes are contained to the playlist folder ----------

def _safe_playlist_path(pl_dir, name):
    p = os.path.normpath(os.path.join(pl_dir, name))
    if os.path.realpath(p) != p or not p.startswith(pl_dir + os.sep):
        raise ValueError("playlist path escapes the playlist folder")
    return p


def list_backups():
    settings = get_settings()
    pl_dir = settings["playlists_dir"]
    out = []
    try:
        for name in sorted(os.listdir(pl_dir)):
            if ".bak-" in name:
                out.append(name)
    except OSError:
        pass
    return out


def delete_backup(name):
    settings = get_settings()
    pl_dir = os.path.realpath(settings["playlists_dir"])
    if ".bak-" not in name:
        raise ValueError("that isn't a backup file")
    p = _safe_playlist_path(pl_dir, name)
    os.remove(p)


def run(dry_run=True):
    """-> {dry_run, log, playlists, totals, error}. Mirrors
    fix-m3u-paths.py's main(): same path-style detection (container/host/
    relative/library-relative), same backup-before-write."""
    settings = get_settings()
    music = cfg.MUSIC_DIR.rstrip("/")
    pl_dir = os.path.realpath(settings["playlists_dir"].rstrip("/"))
    host_root = settings["host_music_root"].rstrip("/")
    croot = music  # this app always sees the library at cfg.MUSIC_DIR

    log = []
    if not _inside(pl_dir, os.path.realpath(music)):
        # Belt and suspenders: save_settings() already rejects this, but
        # /config can be hand-edited directly, so check again at use time.
        return {"dry_run": dry_run, "log": [f"STOP  playlists_dir ({pl_dir}) must be inside {music}."],
                "playlists": [], "totals": {"fixed": 0, "missing": 0, "files": 0},
                "error": "playlists_dir is outside the music library"}
    if not os.path.isdir(music) or not os.path.isdir(pl_dir):
        return {"dry_run": dry_run, "log": [f"STOP  can't find {music} or {pl_dir}."],
                "playlists": [], "totals": {"fixed": 0, "missing": 0, "files": 0}, "error":
                f"can't find {music} or {pl_dir}"}

    log.append(f"{'' if not dry_run else 'DRY RUN, nothing will change. '}Indexing {music} ...")
    idx, n = index_library(music, skip={pl_dir, os.path.join(music, "_playlists")})
    log.append(f"Indexed {n} audio files.")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    tot_fixed = tot_missing = tot_files = 0
    out_playlists = []

    for name in sorted(os.listdir(pl_dir)):
        if not name.lower().endswith((".m3u", ".m3u8")):
            continue
        path = _safe_playlist_path(pl_dir, name)
        raw = open(path, "rb").read()
        bom = raw.startswith(b"\xef\xbb\xbf")
        text = raw.decode("utf-8-sig", errors="replace")
        nl = "\r\n" if "\r\n" in text else "\n"
        lines = text.split(nl)
        out, fixes, misses = [], [], []

        for line in lines:
            entry = line.strip()
            if not entry or entry.startswith("#") or re.match(r"^[a-z]+://", entry, re.I):
                out.append(line)
                continue
            entry = re.sub(r"^\d+:(?=[^/\\])", "", entry)
            if entry.startswith(croot + "/"):
                style, rel = "container", entry[len(croot) + 1:]
            elif host_root and entry.startswith(host_root + "/"):
                style, rel = "host", entry[len(host_root) + 1:]
            elif os.path.isabs(entry):
                out.append(line)
                misses.append((entry, "outside the library"))
                continue
            else:
                beside = os.path.normpath(os.path.join(pl_dir, entry))
                if beside.startswith(music + "/") and os.path.exists(beside):
                    out.append(line)
                    continue
                if os.path.exists(os.path.join(music, entry)):
                    out.append(line)
                    continue
                if entry.startswith(".."):
                    style, rel = "relative", os.path.relpath(beside, music)
                else:
                    style, rel = "library", entry
            if os.path.exists(os.path.join(music, rel)):
                out.append(line)
                continue

            new_rel, note = find_match(rel, idx)
            if not new_rel:
                out.append(line)
                misses.append((rel, note))
                continue
            if style == "container":
                new = f"{croot}/{new_rel}"
            elif style == "host":
                new = f"{host_root}/{new_rel}"
            elif style == "relative":
                new = os.path.relpath(os.path.join(music, new_rel), pl_dir)
            else:
                new = new_rel
            out.append(new)
            fixes.append((rel, new_rel, note))

        if not fixes and not misses:
            continue
        tot_files += 1
        entry_log = [f"{name}: {len(fixes)} fixed, {len(misses)} still missing"]
        for old, new, note in fixes:
            entry_log.append(f"   FIX   {old}\n      -> {new}   ({note})")
        for old, why in misses:
            entry_log.append(f"   MISS  {old}   ({why})")
        log.extend(entry_log)
        tot_fixed += len(fixes)
        tot_missing += len(misses)

        backup = None
        if not dry_run and fixes:
            st = os.stat(path)
            backup = f"{name}.bak-{stamp}"
            shutil.copy2(path, _safe_playlist_path(pl_dir, backup))
            data = nl.join(out)
            with open(path, "w", encoding="utf-8-sig" if bom else "utf-8", newline="") as f:
                f.write(data)
            os.chown(path, st.st_uid, st.st_gid)

        out_playlists.append({
            "name": name, "fixed": [{"old": o, "new": n, "note": nt} for o, n, nt in fixes],
            "missing": [{"old": o, "why": w} for o, w in misses], "backup": backup,
        })

    log.append(f"{tot_files} playlists with broken entries. "
               f"{'Fixed' if not dry_run else 'Can fix'} {tot_fixed}, {tot_missing} have no "
               "match in the library.")
    return {"dry_run": dry_run, "log": log, "playlists": out_playlists,
            "totals": {"fixed": tot_fixed, "missing": tot_missing, "files": tot_files}, "error": None}
