"""Christian / worship artist classification: one CSV allowlist drives a
CATEGORY file tag (see run()/the tagger), a Cluster Cleanup scope, and a
live post-filter on AudioMuse's generated playlists. Ported from the
standalone christian_tag.py (docs/feat-artist-tagging/), rebuilt on top of
app.core.artist_matcher so the name-matching rules are identical to Cluster
Cleanup's.

christian-artists.csv columns: artist,genre,worship,tier,ambiguous,enabled,
mbid,notes,sources,status,release_years,review_flags,source_urls - plus
whatever other columns a future seed update adds. Rows are kept as plain
dicts over whatever fieldnames the file actually has, so unknown columns
round-trip untouched on every save.

worship is three-state (yes/no/unknown): unknown counts as "not worship" for
matching/filtering, but the UI shows it distinctly.
"""
import csv
import io
import os
import re
from dataclasses import dataclass
from pathlib import Path

from mutagen import File as MutagenFile
from mutagen.id3 import TXXX
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4FreeForm

from app.core import config as cfg
from app.core import store
from app.core.artist_matcher import credit_keys, norm
from app.modules.christian_artists import migration

KNOWN_FIELDS = ["artist", "genre", "worship", "tier", "ambiguous", "enabled", "mbid", "notes",
                "sources", "status", "release_years", "review_flags", "source_urls"]
CONTENT_FILTERS = ("any", "christian", "worship", "no_christian")
TOPUP_MULTIPLIERS = (3, 6)
TOPUP_CAP = 200

# ---------- tagger ----------

CATEGORY_TAG = "CATEGORY"
MANAGED_CATEGORIES = ("christian", "worship")
AUDIO_EXT = {".flac", ".mp3", ".m4a", ".ogg", ".opus"}

# Genre tags that look Christian, for the library scan's "Suggestions" panel
# (unchanged from christian_tag.py's CHRISTIAN_GENRE).
CHRISTIAN_GENRE = re.compile(r"christian|ccm|worship|gospel|praise|hymn|inspirational", re.I)

# Prompt-text keywords for the Content filter's auto-suggest (spec's own
# word list, not the genre-tag one above - "church"/"jesus" instead of
# "ccm"/"inspirational").
_WORSHIP_WORDS = re.compile(r"\bworship\b|\bpraise\b|\bhymn\b", re.I)
_CHRISTIAN_WORDS = re.compile(r"\bgospel\b|\bchurch\b|\bchristian\b|\bjesus\b", re.I)

_DEFAULT_CSV = os.path.join(cfg.CONFIG_DEFAULTS_DIR, "christian-artists.csv")
_DEFAULT_OVERRIDES = os.path.join(cfg.CONFIG_DEFAULTS_DIR, "worship-overrides.txt")

DEFAULT_SETTINGS = {"prune": True}


def _csv_file():
    return os.path.join(cfg.CONFIG_DIR, "christian-artists.csv")


def _overrides_file():
    return os.path.join(cfg.CONFIG_DIR, "worship-overrides.txt")


def _settings_file():
    return os.path.join(cfg.CONFIG_DIR, "christian-tagging-settings.json")


def ensure_seeded():
    store.seed_if_missing(_csv_file(), _DEFAULT_CSV)
    store.seed_if_missing(_overrides_file(), _DEFAULT_OVERRIDES)
    migration.migrate_if_needed(_csv_file())


def get_settings():
    return dict(DEFAULT_SETTINGS, **store.load_json(_settings_file(), {}))


def save_settings(**kw):
    settings = get_settings()
    settings.update({k: v for k, v in kw.items() if v is not None})
    store.save_json(_settings_file(), settings)
    return settings


# ---------- yes/no/unknown helpers ----------

def _yes(v):
    return (v or "").strip().lower() in {"yes", "y", "true", "1"}


def _worship_state(v):
    v = (v or "").strip().lower()
    if v in {"yes", "y", "true", "1"}:
        return "yes"
    if v in {"no", "n", "false", "0"}:
        return "no"
    return "unknown"


@dataclass
class Artist:
    name: str
    genre: str
    worship: str  # "yes" | "no" | "unknown"
    tier: str
    ambiguous: bool
    enabled: bool
    mbids: frozenset

    @property
    def worship_effective(self):
        return self.worship == "yes"


def _row_to_artist(row):
    return Artist(
        name=(row.get("artist") or "").strip(),
        genre=(row.get("genre") or "").strip(),
        worship=_worship_state(row.get("worship", "")),
        tier=(row.get("tier") or "core").strip(),
        ambiguous=_yes(row.get("ambiguous", "")),
        enabled=_yes(row.get("enabled", "yes")),
        mbids=frozenset(m.strip().lower() for m in re.split(r"[;,\s]+", row.get("mbid") or "") if m.strip()),
    )


class Matcher:
    """by_name: enabled artists with no mbid. by_mbid: enabled artists with
    one, keyed by each mbid - these are deliberately *not* also in by_name,
    so an ambiguous name with a confirmed mbid can't still false-positive
    match by name. disabled_by_name: everything ambiguous/crossover/disabled,
    kept so the library scan can flag "this disabled entry matched your
    library" without matching it for real."""

    def __init__(self, artists):
        self.by_name = {}
        self.by_mbid = {}
        self.disabled_by_name = {}
        for a in artists:
            if not a.enabled:
                self.disabled_by_name[norm(a.name)] = a
            elif a.mbids:
                for m in a.mbids:
                    self.by_mbid[m] = a
            else:
                self.by_name[norm(a.name)] = a

    def match_by_name(self, keys):
        return [self.by_name[k] for k in keys if k in self.by_name]

    def match(self, keys, mbids=frozenset()):
        hits = self.match_by_name(keys)
        hits += [self.by_mbid[m] for m in mbids if m in self.by_mbid]
        return hits


@dataclass
class Overrides:
    albums: dict
    tracks: dict

    @classmethod
    def parse(cls, text):
        albums, tracks, warnings = {}, {}, []
        for line in (text or "").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            value = not line.startswith("!")
            parts = [norm(p) for p in line.lstrip("!").split("|")]
            if len(parts) == 2:
                albums[(parts[0], parts[1])] = value
            elif len(parts) == 3:
                tracks[(parts[0], parts[1], parts[2])] = value
            else:
                warnings.append(line)
        return cls(albums, tracks), warnings

    def lookup(self, artist_keys, album, title):
        a, t = norm(album), norm(title)
        for k in artist_keys:  # track beats album
            if (k, a, t) in self.tracks:
                return self.tracks[(k, a, t)]
        for k in artist_keys:
            if (k, a) in self.albums:
                return self.albums[(k, a)]
        return None


# ---------- CSV load/save, with unknown columns round-tripped untouched ----------

_cache = {"mtime": None, "fieldnames": None, "rows": None, "matcher": None}
_ov_cache = {"mtime": None, "overrides": None, "warnings": None}


def _parse_csv(text):
    reader = csv.DictReader(io.StringIO(text or ""))
    fieldnames = reader.fieldnames or list(KNOWN_FIELDS)
    rows = [r for r in reader if (r.get("artist") or "").strip()
            and not r["artist"].strip().startswith("#")]
    return fieldnames, rows


def _write_csv(fieldnames, rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in fieldnames})
    store.save_text(_csv_file(), buf.getvalue())
    _cache.update(mtime=None, fieldnames=None, rows=None, matcher=None)


def _load():
    """-> (fieldnames, rows, matcher), reloaded when the CSV's mtime changes
    or after a save invalidates the cache."""
    ensure_seeded()
    path = _csv_file()
    try:
        mtime = os.stat(path).st_mtime
    except OSError:
        mtime = None
    if _cache["mtime"] != mtime or _cache["rows"] is None:
        fieldnames, rows = _parse_csv(store.load_text(path, ""))
        matcher = Matcher([_row_to_artist(r) for r in rows])
        _cache.update(mtime=mtime, fieldnames=fieldnames, rows=rows, matcher=matcher)
    return _cache["fieldnames"], _cache["rows"], _cache["matcher"]


def get_artists_text():
    ensure_seeded()
    return store.load_text(_csv_file())


def save_artists_text(text):
    store.save_text(_csv_file(), text)
    _cache.update(mtime=None, fieldnames=None, rows=None, matcher=None)


def get_artist_rows():
    """Every artist row (including unknown/provenance columns), for the UI table."""
    _, rows, _ = _load()
    return rows


def get_matcher():
    return _load()[2]


def get_overrides():
    ensure_seeded()
    path = _overrides_file()
    try:
        mtime = os.stat(path).st_mtime
    except OSError:
        mtime = None
    if _ov_cache["mtime"] != mtime or _ov_cache["overrides"] is None:
        overrides, warnings = Overrides.parse(store.load_text(path, ""))
        _ov_cache.update(mtime=mtime, overrides=overrides, warnings=warnings)
    return _ov_cache["overrides"]


def get_overrides_warnings():
    get_overrides()
    return _ov_cache["warnings"] or []


def get_overrides_text():
    ensure_seeded()
    return store.load_text(_overrides_file())


def save_overrides_text(text):
    store.save_text(_overrides_file(), text)
    _ov_cache.update(mtime=None, overrides=None, warnings=None)


# ---------- single-artist CRUD + bulk add ----------

def _by_norm_name(rows):
    return {norm(r.get("artist", "")): r for r in rows}


def add_artist(artist, genre="", worship="no", tier="core", ambiguous=False,
               enabled=True, mbid="", notes=""):
    artist = (artist or "").strip()
    if not artist:
        raise ValueError("Artist name can't be empty.")
    fieldnames, rows, _ = _load()
    key = norm(artist)
    existing = _by_norm_name(rows)
    if key in existing:
        raise ValueError(f'"{artist}" is already on the list (as "{existing[key].get("artist")}").')
    row = {k: "" for k in fieldnames}
    row.update(artist=artist, genre=genre, worship=worship, tier=tier,
                ambiguous="yes" if ambiguous else "no", enabled="yes" if enabled else "no",
                mbid=mbid, notes=notes)
    rows.append(row)
    _write_csv(fieldnames, rows)
    return row


def update_artist(name, **fields):
    fieldnames, rows, _ = _load()
    key = norm(name)
    row = next((r for r in rows if norm(r.get("artist", "")) == key), None)
    if row is None:
        raise KeyError(f'No artist named "{name}" on the list.')
    for k, v in fields.items():
        if v is not None:
            row[k] = v
    _write_csv(fieldnames, rows)
    return row


def delete_artist(name):
    fieldnames, rows, _ = _load()
    key = norm(name)
    new_rows = [r for r in rows if norm(r.get("artist", "")) != key]
    if len(new_rows) == len(rows):
        raise KeyError(f'No artist named "{name}" on the list.')
    _write_csv(fieldnames, new_rows)


def bulk_add(names, genre="", worship="no", tier="core", enabled=True):
    fieldnames, rows, _ = _load()
    existing = set(_by_norm_name(rows))
    added, duplicates, seen = [], [], set()
    for raw in names:
        name = (raw or "").strip()
        if not name:
            continue
        key = norm(name)
        if key in existing or key in seen:
            duplicates.append(name)
            continue
        seen.add(key)
        row = {k: "" for k in fieldnames}
        row.update(artist=name, genre=genre, worship=worship, tier=tier,
                    ambiguous="no", enabled="yes" if enabled else "no", mbid="", notes="bulk add")
        rows.append(row)
        added.append(name)
    _write_csv(fieldnames, rows)
    return {"added": added, "duplicates": duplicates}


def export_csv_path():
    ensure_seeded()
    return _csv_file()


def reset_to_defaults():
    """Merge-only: add any shipped-default artist missing from the current
    list. Never overwrites or removes a user's existing row."""
    fieldnames, rows, _ = _load()
    existing = set(_by_norm_name(rows))
    _, default_rows = _parse_csv(store.load_text(_DEFAULT_CSV, ""))
    added = 0
    for r in default_rows:
        key = norm(r.get("artist", ""))
        if key and key not in existing:
            row = {k: "" for k in fieldnames}
            row.update({k: r.get(k, "") for k in fieldnames if k in r})
            rows.append(row)
            existing.add(key)
            added += 1
    _write_csv(fieldnames, rows)
    return {"added": added}


def seed_diff():
    """What reset_to_defaults() would add, without writing anything."""
    _, rows, _ = _load()
    existing = set(_by_norm_name(rows))
    _, default_rows = _parse_csv(store.load_text(_DEFAULT_CSV, ""))
    new_names = [r.get("artist") for r in default_rows if norm(r.get("artist", "")) not in existing]
    return {"new_count": len(new_names), "sample": new_names[:25]}


def migration_log():
    return migration.last_log()


# ---------- classification ----------

def classify(artist_credit, album="", title="", mbids=frozenset()):
    """-> {"christian": bool, "worship": bool}. worship implies christian."""
    matcher = get_matcher()
    keys = credit_keys(artist_credit or "")
    hits = matcher.match(keys, mbids)
    christian = bool(hits)
    worship = any(h.worship_effective for h in hits)
    if christian:
        ov = get_overrides().lookup(keys, album, title)
        if ov is not None:
            worship = ov
    return {"christian": christian, "worship": christian and worship}


def scoped_name_keys(scope="christian"):
    """Normalized name keys of every *enabled* artist in scope, for Cluster
    Cleanup - name-only, same as its previous flat-text-list matching."""
    _, rows, _ = _load()
    keys = set()
    for r in rows:
        a = _row_to_artist(r)
        if not a.enabled:
            continue
        if scope == "worship" and not a.worship_effective:
            continue
        keys.add(norm(a.name))
    return frozenset(keys)


def suggest_content_filter(text):
    """Auto-suggest for the prompt/instruction text box - a suggestion the
    user can change, not a lock."""
    text = text or ""
    if _WORSHIP_WORDS.search(text):
        return "worship"
    if _CHRISTIAN_WORDS.search(text):
        return "christian"
    return None


def suggest_from_anchors(anchor_artists):
    """If every Alchemy anchor is worship, suggest Worship only; if every one
    is at least Christian, suggest Christian only; else no suggestion."""
    if not anchor_artists:
        return None
    classifications = [classify(a) for a in anchor_artists]
    if all(c["worship"] for c in classifications):
        return "worship"
    if all(c["christian"] for c in classifications):
        return "christian"
    return None


def _keep_track(t, content_filter):
    if content_filter == "any":
        return True
    c = classify(t.get("artist") or "", t.get("album") or "", t.get("title") or "")
    if content_filter == "christian":
        return c["christian"]
    if content_filter == "worship":
        return c["worship"]
    if content_filter == "no_christian":
        return not c["christian"]
    return True


def _filter_once(tracks, content_filter):
    kept, filtered_out = [], []
    for t in tracks:
        (kept if _keep_track(t, content_filter) else filtered_out).append(t)
    return kept, filtered_out


def apply_content_filter(tracks, content_filter, goal=None, fetch_more=None):
    """tracks: the initial AudioMuse result. goal: how many kept tracks we're
    trying to reach via top-up (defaults to len(tracks) - "try to get back to
    what we started with"). fetch_more(n), if given, re-requests AudioMuse
    with a bigger n/size and returns a fresh batch of the same track shape.
    -> {"kept", "filtered_out", "short"}, AudioMuse's order preserved,
    deduplicated by id."""
    if content_filter not in CONTENT_FILTERS or content_filter == "any" or not tracks:
        return {"kept": list(tracks), "filtered_out": [], "short": False}
    goal = len(tracks) if goal is None else goal
    kept, filtered_out = _filter_once(tracks, content_filter)
    seen = {t["id"] for t in kept if t.get("id")}
    filtered_seen = {t["id"] for t in filtered_out if t.get("id")}
    base_n = max(len(tracks), 1)
    if fetch_more is not None:
        for mult in TOPUP_MULTIPLIERS:
            if len(kept) >= goal:
                break
            bigger_n = min(base_n * mult, TOPUP_CAP)
            more = fetch_more(bigger_n) or []
            more_kept, more_filtered = _filter_once(more, content_filter)
            for t in more_kept:
                tid = t.get("id")
                if tid and tid not in seen:
                    kept.append(t)
                    seen.add(tid)
            for t in more_filtered:
                tid = t.get("id")
                if tid and tid not in filtered_seen:
                    filtered_out.append(t)
                    filtered_seen.add(tid)
            if bigger_n >= TOPUP_CAP:
                break
    return {"kept": kept, "filtered_out": filtered_out, "short": len(kept) < goal}


# ---------- tagger file I/O (ported from christian_tag.py's already-correct,
# format-specific read/write - unchanged) ----------

def _read_track_info(path):
    f = MutagenFile(path, easy=True)
    if f is None or f.tags is None:
        return None
    t = f.tags
    get = lambda k: [str(v) for v in t.get(k, [])]
    mbids = {m.lower() for v in get("musicbrainz_artistid") + get("musicbrainz_albumartistid")
              for m in re.split(r"[;/\s]+", v) if m}
    return {"names": get("albumartist") + get("artist"), "mbids": mbids,
            "album": (get("album") or [""])[0], "title": (get("title") or [""])[0],
            "genres": get("genre")}


def _get_category(f):
    if f.tags is None:
        return []
    if isinstance(f, MP3):
        return [str(x) for fr in f.tags.getall(f"TXXX:{CATEGORY_TAG}") for x in fr.text]
    if isinstance(f, MP4):
        return [bytes(v).decode("utf-8", "ignore")
                for v in f.tags.get(f"----:com.apple.iTunes:{CATEGORY_TAG}", [])]
    return [str(v) for v in f.tags.get(CATEGORY_TAG, [])]


def _set_category(f, values):
    if f.tags is None:
        f.add_tags()
    if isinstance(f, MP3):
        f.tags.delall(f"TXXX:{CATEGORY_TAG}")
        if values:
            f.tags.add(TXXX(encoding=3, desc=CATEGORY_TAG, text=values))
    elif isinstance(f, MP4):
        key = f"----:com.apple.iTunes:{CATEGORY_TAG}"
        if key in f.tags:
            del f.tags[key]
        if values:
            f.tags[key] = [MP4FreeForm(v.encode("utf-8")) for v in values]
    else:
        if CATEGORY_TAG in f.tags:
            del f.tags[CATEGORY_TAG]
        if values:
            f.tags[CATEGORY_TAG] = values
    f.save()


def _desired_category(current, christian, worship):
    keep = [v for v in current if v.strip().lower() not in MANAGED_CATEGORIES]
    return keep + (["christian"] if christian else []) + (["worship"] if christian and worship else [])


def run(dry_run=True):
    """-> {dry_run, log, changed, unchanged, errors, counts, error}. Ported
    from christian_tag.py's main(): preserves every non-christian/worship
    CATEGORY value and never touches any other tag, skips files already
    correct (no rewrite, no mtime bump), prunes stale values unless
    settings.prune is off, skips /music/.dupe-quarantine/, never follows
    symlinks, only ever touches paths under MUSIC_DIR."""
    ensure_seeded()
    settings = get_settings()
    prune = bool(settings.get("prune", True))
    music_root = Path(os.path.realpath(cfg.MUSIC_DIR))

    log = []
    changed = unchanged = errors = 0
    counts = {"christian": 0, "worship": 0}

    try:
        files = sorted(p for p in music_root.rglob("*")
                        if p.suffix.lower() in AUDIO_EXT and p.is_file() and not p.is_symlink()
                        and ".dupe-quarantine" not in p.parts)
    except OSError as e:
        return {"dry_run": dry_run, "log": [f"STOP  can't read {music_root}: {e}"],
                "changed": 0, "unchanged": 0, "errors": 0, "counts": counts, "error": str(e)}

    for p in files:
        try:
            info = _read_track_info(p)
            if info is None:
                continue
            keys = set()
            for n in info["names"]:
                keys |= credit_keys(n)
            matcher = get_matcher()
            hits = matcher.match(keys, info["mbids"])
            christian = bool(hits)
            worship = any(h.worship_effective for h in hits)
            if christian:
                ov = get_overrides().lookup(keys, info["album"], info["title"])
                if ov is not None:
                    worship = ov
            counts["christian"] += christian
            counts["worship"] += christian and worship

            f = MutagenFile(p)
            if f is None:
                continue
            current = _get_category(f)
            has_managed = any(v.strip().lower() in MANAGED_CATEGORIES for v in current)
            if not christian and (not prune or not has_managed):
                continue
            want = _desired_category(current, christian, worship)
            if want == current:
                unchanged += 1
                continue
            log.append(f"{'WRITE' if not dry_run else 'would write'}  {want or '(remove)'}  {p}")
            if not dry_run:
                _set_category(f, want)
            changed += 1
        except Exception as e:
            errors += 1
            log.append(f"ERROR  {p}: {e}")

    log.insert(0, f"{'DRY RUN, nothing will change. ' if dry_run else ''}"
                  f"{changed} to change, {unchanged} already correct, {errors} errors")
    return {"dry_run": dry_run, "log": log, "changed": changed, "unchanged": unchanged,
            "errors": errors, "counts": counts, "error": None}


# ---------- library scan ----------
#
# Reads tags directly via mutagen (the same easy=True reader the tagger
# uses) rather than duplicate_finder's tags.db cache: that cache's raw tag
# dict keys ID3 TXXX frames by their literal (space-separated) description
# ("musicbrainz artist id"), while the MBID prefill this scan needs relies
# on mutagen's easy-tag key normalization ("musicbrainz_artistid") to read
# that correctly across FLAC/MP3/M4A alike - reusing the cache's fields
# would silently misread MBIDs on MP3 files. A future pass could extend that
# cache with an easy-tag-shaped column instead of re-reading every file.

def scan_library():
    """-> {needs_decision, suggestions, not_in_library, library_counts} - see
    the Christian artists page spec: disabled/ambiguous entries that do show
    up in the library, library artists that look Christian by genre tag but
    aren't on the list, enabled entries with no matching tracks, and a
    per-artist track count for the table's "tracks in library" column."""
    ensure_seeded()
    _, rows, matcher = _load()
    all_known = {norm(r.get("artist", "")) for r in rows}
    found_known = set()
    needs_decision = {}
    suggestions = {}
    library_counts = {}

    music_root = Path(os.path.realpath(cfg.MUSIC_DIR))
    try:
        files = [p for p in music_root.rglob("*")
                 if p.suffix.lower() in AUDIO_EXT and p.is_file() and not p.is_symlink()
                 and ".dupe-quarantine" not in p.parts]
    except OSError:
        files = []

    for p in files:
        try:
            info = _read_track_info(p)
        except Exception:
            continue
        if info is None or not info["names"]:
            continue
        keys = set()
        for n in info["names"]:
            keys |= credit_keys(n)
        hit_keys = keys & all_known
        found_known |= hit_keys
        for key in hit_keys:
            library_counts[key] = library_counts.get(key, 0) + 1
        for key in keys:
            a = matcher.disabled_by_name.get(key)
            if a is not None:
                slot = needs_decision.setdefault(
                    key, {"name": a.name, "albums": set(), "mbids": set(), "count": 0})
                slot["albums"].add(info["album"])
                slot["mbids"] |= info["mbids"]
                slot["count"] += 1
        if not (keys & all_known) and any(CHRISTIAN_GENRE.search(g) for g in info["genres"]):
            display = info["names"][0] if info["names"] else "?"
            slot = suggestions.setdefault(norm(display), {"name": display, "genres": set(), "count": 0})
            slot["genres"] |= set(info["genres"])
            slot["count"] += 1

    not_in_library = sorted(
        (r.get("artist") for r in rows
         if _yes(r.get("enabled", "yes")) and norm(r.get("artist", "")) not in found_known),
        key=str.casefold)
    counts_by_display_name = {r.get("artist"): library_counts[norm(r.get("artist", ""))]
                               for r in rows if norm(r.get("artist", "")) in library_counts}

    result = {
        "needs_decision": [
            {"name": v["name"], "albums": sorted(a for a in v["albums"] if a)[:5],
             "mbid_suggestion": next(iter(v["mbids"])) if len(v["mbids"]) == 1 else None,
             "count": v["count"]}
            for v in sorted(needs_decision.values(), key=lambda v: v["name"].casefold())
        ],
        "suggestions": [
            {"name": v["name"], "genres": sorted(v["genres"]), "count": v["count"]}
            for v in sorted(suggestions.values(), key=lambda v: v["name"].casefold())
        ],
        "library_counts": counts_by_display_name,
        "not_in_library": not_in_library,
    }
    store.save_json(_scan_file(), result)
    return result


def _scan_file():
    return os.path.join(cfg.CONFIG_DIR, "christian-artists-last-scan.json")


def last_scan():
    """The last scan_library() result, or None if it's never been run."""
    return store.load_json(_scan_file(), None)
