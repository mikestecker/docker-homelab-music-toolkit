"""One-time migration from Cluster Cleanup's old flat-text worship artist
list into christian-artists.csv.

config-defaults/worship-artists.txt is deleted as part of shipping this
feature (Cluster Cleanup no longer reads it), so the "diff against the
shipped default" logic below can't read that file from disk in a new
install - _SHIPPED_ACTIVE/_SHIPPED_GRAYAREA are a one-time snapshot of its
content, taken at the time this migration was written. Doesn't need to track
future changes: this code only ever runs against *old* installs that still
have a `/config/worship-artists.txt` from before this feature existed.

Only lines the user touched count:
  - A line they added (not a name from either list below) -> worship=yes, enabled=yes.
  - A shipped-active line they commented out or deleted -> enabled=no.
  - A shipped gray-area line (shipped commented, "OFF by default") they
    uncommented -> worship=yes, enabled=yes.
Untouched gray-area lines are left alone - they get whatever classification
the new seed CSV already gives them.

Runs once, gated on worship-artists.txt existing and worship-artists.txt.migrated
not existing yet; renames the old file to .migrated (never deletes it) and
writes a log of what was imported, even if nothing changed.
"""
import csv
import io
import os
import time

from app.core import config as cfg
from app.core import store
from app.core.artist_matcher import norm

_OLD_FILE = "worship-artists.txt"
_LOG_FILE = "christian-artists-migration-log.json"

# Snapshot of config-defaults/worship-artists.txt as shipped before this
# feature, in two groups: the 228 uncommented ("active") lines, and the 23
# commented "Review: gray area, OFF by default" lines.
_SHIPPED_ACTIVE = [
    "Passion", "Charlie Hall", "Hillsong UNITED", "Big Tent Revival", "The Kry", "Ascend the Hill",
    "Hillsong Worship", "Hillsong Young & Free", "Hillsong", "Elevation Worship", "Elevation Rhythm",
    "Maverick City Music", "Bethel Music", "Jesus Culture", "Planetshakers", "Gateway Worship",
    "Vertical Worship", "Housefires", "UPPERROOM", "Red Rocks Worship", "River Valley Worship",
    "River Valley AGES", "LO Worship", "SEU Worship", "Sons of Sunday", "CityAlight", "Shane & Shane",
    "The Worship Initiative", "Sovereign Grace Music", "North Point Worship", "Life.Church Worship",
    "Bethany Music", "Influence Music", "Kingdom Culture Worship", "Victory Worship", "New Life Worship",
    "Grace Worship", "Transformation Worship", "West Coast Revival", "Worship Circle", "Calvary Creative",
    "Celtic Worship", "Isla Vista Worship", "The Village Church", "Redeemer Christian Church",
    "Red Mountain Church", "Reach Church", "Project 1:11 Lansing", "Frontline Music", "Emu Music",
    "Exodus Music", "Simply Worship", "The Secret Place", "Draw Close", "All Sons & Daughters",
    "Bryan & Katie Torwalt", "Kari Jobe", "Kari Jobe Carnes", "Cody Carnes", "Brandon Lake",
    "Chris Tomlin", "Phil Wickham", "Matt Redman", "Tim Hughes", "Martin Smith", "Kristian Stanfill",
    "Christy Nockels", "Nathan Nockels", "Chris Brown", "Chandler Moore", "Naomi Raine", "Pat Barrett",
    "Leeland", "Josh Baldwin", "Steffany Gretzinger", "Jenn Johnson", "Brian Johnson",
    "Brian & Jenn Johnson", "Jeremy Riddle", "Kim Walker-Smith", "Bryan McCleery", "Tiffany Hudson",
    "Melodie Malone", "Brooke Ligertwood", "Reuben Morgan", "Joel Houston", "Taya", "Aodhan King",
    "Darlene Zschech", "Paul Baloche", "Don Moen", "Israel Houghton", "Michael W. Smith",
    "Lincoln Brewster", "Meredith Andrews", "Kristene DiMarco", "Amanda Cook", "Hannah Hobbs",
    "Hope Darst", "Mack Brock", "Sean Feucht", "David Brymer", "Aaron Keyes", "Aaron Shust",
    "Tommy Walker", "Vineyard Worship", "Matt Maher", "Matt Maher & Friends", "Hillsong Kids",
    "Integrity Worship Singers", "Maranatha! Music", "Maranatha! Praise Band", "Passion Worship Band",
    "Keith & Kristyn Getty", "Getty Music", "Stuart Townend", "Graham Kendrick", "Matt Boswell",
    "Matt Papa", "Matt Boswell & Matt Papa", "Page CXVI", "Page CXVI - Reimagined by Derek Webb",
    "Kings Kaleidoscope Hymns", "Hope Hymns", "High Street Hymns", "Holy City Hymns", "City Hymns",
    "Hymns of Grace", "Hymns of the People", "Indelible Grace Music", "Sojourn Music",
    "Cardiphonia Music", "Norton Hall Band", "The Enfield Hymn Sessions", "The Franz Brothers",
    "Brian Sauve", "Bob Kauflin", "Dave Hunt", "A New Liturgy", "Greg Attwells", "Providence",
    "Salt of the Sound", "Fernando Ortega", "Thief to King", "Dear Gravity", "Daniel Martin Moore",
    "Adam Wheatley", "The Journey Collective", "Ken Verheecke", "My Soul Among Lions", "Servants",
    "Sojourners", "She Reads Truth", "The Gospel Coalition", "Fount", "Nathan Clark George",
    "Gregory Wilbur", "Redeemer Presbyterian Church", "Asaph's Arrows", "The Lower Lights",
    "Wilder Adkins", "Paul Zach", "Nathan Drake", "Christopher Galovan", "Chris Rice", "John Ofa Rhee",
    "Alabaster Co.", "Simon Wester", "The Lofi Christian", "Lofi Worship", "Lofi Hymns.",
    "Pathway Piano", "Piano Praises", "Carl Eksmo", "Tony Anderson", "Dan Musselman", "Stian Jarrell",
    "Jim Brickman", "Adam Zampino", "Michele McLaughlin", "Manuel Elastic", "Sarah Brooks",
    "Joshua David Harris", "Khamir Music", "Huckleberry Flint", "Kendra Logozar", "Michael Logozar",
    "Eric Gilmour", "MercyMe", "Casting Crowns", "Steven Curtis Chapman", "Twila Paris",
    "Point of Grace", "Avalon", "Natalie Grant", "Jason Gray", "Sanctus Real", "Tenth Avenue North",
    "Building 429", "Big Daddy Weave", "Matthew West", "Mark Schultz", "Jaci Velasquez",
    "Rebecca St. James", "Nichole Nordeman", "Bebo Norman", "Phillips, Craig & Dean", "4Him",
    "Margaret Becker", "Rich Mullins", "Ginny Owens", "Out of Eden", "Zoegirl", "BarlowGirl",
    "Sara Groves", "Danny Gokey", "Lauren Daigle", "Zach Williams", "Jeremy Camp", "Unspoken",
    "Jordan Feliz", "Cain", "Anne Wilson", "Josh Wilson", "Francesca Battistelli", "Selah",
    "Sidewalk Prophets", "Hawk Nelson",
]
_SHIPPED_GRAYAREA = [
    "Crowder", "David Crowder Band", "Kings Kaleidoscope", "Citizens", "Citizens & Saints",
    "Chris Renzema", "John Mark Pantana", "Rivers & Robots", "Rend Collective", "Josh Garrels",
    "Third Day", "Delirious?", "Newsboys", "TobyMac", "Audio Adrenaline", "Jars of Clay",
    "Forrest Frank", "Josiah Queen", "We The Kingdom", "for KING & COUNTRY", "Tauren Wells",
    "Hulvey", "Local Sound",
]


def _old_path():
    return os.path.join(cfg.CONFIG_DIR, _OLD_FILE)


def _migrated_path():
    return _old_path() + ".migrated"


def _log_path():
    return os.path.join(cfg.CONFIG_DIR, _LOG_FILE)


def last_log():
    return store.load_json(_log_path(), None)


def _user_active_names(text):
    return {norm(line.strip()) for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")}


def migrate_if_needed(csv_path):
    old_path = _old_path()
    if not os.path.exists(old_path) or os.path.exists(_migrated_path()):
        return None

    text = store.load_text(old_path, "")
    user_active = _user_active_names(text)
    shipped_active = {norm(n): n for n in _SHIPPED_ACTIVE}
    shipped_gray = {norm(n): n for n in _SHIPPED_GRAYAREA}
    user_original = {}
    for line in text.splitlines():
        s = line.strip()
        if s:
            name = s.lstrip("#").strip()
            user_original.setdefault(norm(name), name)

    to_enable_worship = (user_active - set(shipped_active) - set(shipped_gray)) | \
                         (set(shipped_gray) & user_active)
    to_disable = set(shipped_active) - user_active

    def display(key):
        return user_original.get(key) or shipped_active.get(key) or shipped_gray.get(key) or key

    changed = bool(to_enable_worship or to_disable)
    if changed:
        with open(csv_path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            fieldnames = reader.fieldnames or []
            rows = [r for r in reader if (r.get("artist") or "").strip()]
        existing = {norm(r.get("artist", "")): r for r in rows}

        for key in to_enable_worship:
            row = existing.get(key)
            if row is None:
                row = {k: "" for k in fieldnames}
                row.update(artist=display(key), genre="unknown", tier="core",
                            ambiguous="no", mbid="", notes="migrated from worship-artists.txt")
                rows.append(row)
                existing[key] = row
            row["worship"] = "yes"
            row["enabled"] = "yes"
        for key in to_disable:
            row = existing.get(key)
            if row is not None:
                row["enabled"] = "no"

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in fieldnames})
        store.save_text(csv_path, buf.getvalue())

    log = {
        "changed": changed,
        "migrated_at": time.time(),
        "worship_enabled": sorted(display(k) for k in to_enable_worship),
        "disabled": sorted(display(k) for k in to_disable),
    }
    store.save_json(_log_path(), log)
    os.replace(old_path, _migrated_path())
    return log
