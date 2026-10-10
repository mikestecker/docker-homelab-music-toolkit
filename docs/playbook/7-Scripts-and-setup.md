# Scripts and setup

Every script we've written for AudioMuse, Navidrome and the NAS, with its full source, where it lives, how it's set up and what runs it. If you ever rebuild the NAS, this tab plus the Navidrome plugins tab is enough to put it all back.

All of them use only the Python standard library (or plain bash), so they run on the TrueNAS host as is. No pip installs, no containers.

## What's where

| Script | Folder on the NAS | What it does | How it runs |
| --- | --- | --- | --- |
| `clean-clusters.py` + `worship-artists.txt` + `cleanup.env` | `/mnt/ssd-pool/apps/audiomuse/cluster-cleanup/` | Takes stray worship songs out of AudioMuse's `_automatic` cluster playlists | Daily cron (set up) |
| `tag-tidarr-playlists.py` | `/mnt/ssd-pool/apps/navidrome/scripts/` | Files Tidarr's imported playlists under `Imports/Tidarr/` | By hand, or a daily cron (suggested, not set up yet) |
| `rename-playlists.py` + `playlist-folders.txt` | `/mnt/ssd-pool/apps/navidrome/scripts/` | Renames playlists into folders from a map file | By hand, after you edit the map |
| `navidrome.env` | `/mnt/ssd-pool/apps/navidrome/scripts/` | Login for the two scripts above | Read by them |
| `fix-m3u-paths.py` | `/mnt/ssd-pool/apps/navidrome/scripts/` | Repoints broken `.m3u` entries after re-downloads | By hand, when Navidrome logs "Path in playlist not found" |
| `update-navidrome-plugins.sh` | `/mnt/ssd-pool/apps/navidrome/` | Installs and updates the five Navidrome plugins | Weekly cron, Sundays 05:00 (source and setup in the Navidrome plugins tab) |
| Smart playlists (`.nsp`) | `/mnt/tank/media/music/_playlists/` | Recently Added, Forgotten Favorites, per-artist lists, etc. | Navidrome reads them itself (steps in the Recreating playlists tab, method 3) |
| ZFS ARC cap | TrueNAS Init/Shutdown Scripts | Caps the ARC at 14 GiB so apps don't get squeezed | Post Init, every boot |

## Cron jobs

All in TrueNAS under **System → Advanced Settings → Cron Jobs → Add**, Run As User `root`. Root is needed because the `.env` files are `chmod 600` and owned by root.

| Job | Command | Schedule | Status |
| --- | --- | --- | --- |
| Clean cluster playlists | `python3 /mnt/ssd-pool/apps/audiomuse/cluster-cleanup/clean-clusters.py` | Daily | Set up |
| File Tidarr imports | `python3 /mnt/ssd-pool/apps/navidrome/scripts/tag-tidarr-playlists.py --apply` | Daily, 06:15 | Suggested |
| Update Navidrome plugins | `/mnt/ssd-pool/apps/navidrome/update-navidrome-plugins.sh >> /mnt/ssd-pool/apps/navidrome/plugin-updates.log 2>&1` | Sundays, 05:00 | See Navidrome plugins tab |

The cleanup script writes its own log (`clean-clusters.log`, rotated at 1 MB), so its cron line doesn't need a `>>` redirect. Check what the last runs did with:

```bash
sudo tail -50 /mnt/ssd-pool/apps/audiomuse/cluster-cleanup/clean-clusters.log
```

## Putting a script on the NAS

The same steps work for every script below. From the TrueNAS shell:

```bash
sudo mkdir -p /mnt/ssd-pool/apps/navidrome/scripts
sudo nano /mnt/ssd-pool/apps/navidrome/scripts/tag-tidarr-playlists.py    # paste the code block, Ctrl+O, Enter, Ctrl+X
```

Or copy the files I sent in chat over SMB into the same folder. Either way, run each script once without `--apply` (or with `DRY_RUN=1`) first. They all default to a dry run that only reports.

## ZFS ARC cap

After the NAS crash, the ARC is capped at 14 GiB (15032385536 bytes) so Docker apps keep enough memory.

In TrueNAS go to **System → Advanced Settings → Init/Shutdown Scripts → Add**:

- Type: Command
- Command: `echo 15032385536 > /sys/module/zfs/parameters/zfs_arc_max`
- When: Post Init
- Enabled: on

Check it took effect after a reboot:

```bash
cat /sys/module/zfs/parameters/zfs_arc_max     # 15032385536
arc_summary | grep -i 'max size'
```

## clean-clusters.py

AudioMuse clusters by sound only, so big guitar worship (Passion, Hillsong UNITED) lands in alt-rock and skate clusters. This removes songs by artists in `worship-artists.txt` from the `_automatic` playlists, but only when they're a minority of the playlist (`MAX_SHARE`). A cluster that's mostly worship is left alone. The clustering tuning that goes with it is in the main tab under Tuning clustering.

### Setup

```bash
D=/mnt/ssd-pool/apps/audiomuse/cluster-cleanup
sudo mkdir -p "$D"
# put clean-clusters.py, worship-artists.txt and cleanup.env.example in $D, then:
sudo cp "$D/cleanup.env.example" "$D/cleanup.env"
sudo nano "$D/cleanup.env"          # ND_USER / ND_PASS = the Navidrome user AudioMuse uses
sudo chown root:root "$D/cleanup.env" && sudo chmod 600 "$D/cleanup.env"

sudo python3 "$D/clean-clusters.py"                  # dry run, reads DRY_RUN=1 from the file
sudo sed -i 's/^DRY_RUN=1/DRY_RUN=0/' "$D/cleanup.env"  # once the dry run looks right
```

Then add the daily cron job from the table above.

### Changing it later

```bash
D=/mnt/ssd-pool/apps/audiomuse/cluster-cleanup
sudo grep -v PASS "$D/cleanup.env"                          # see current settings
sudo sed -i 's/^MAX_SHARE=.*/MAX_SHARE=0.30/' "$D/cleanup.env"   # keep clusters that are 31%+ worship
sudo sed -i 's|^RENAME_PREFIX=.*|RENAME_PREFIX=AudioMuse/Clusters/|' "$D/cleanup.env"
sudo DRY_RUN=1 python3 "$D/clean-clusters.py"             # one-off dry run, whatever the file says
sudo nano "$D/worship-artists.txt"                         # add or remove artists, or un-# the review section
```

**Options in `cleanup.env`:**

- `MAX_SHARE` (0.34): remove listed artists only when they're at most this share of a playlist. 0.30 keeps the Alternative Sunday Drive kind of cluster (31% worship) intact.
- `MIN_SECONDS` (0): also drop tracks shorter than this, for intros and interludes.
- `RENAME_PREFIX` (blank): file the clusters in a folder, e.g. `AudioMuse/Clusters/`. The `_automatic` ending stays, because that's how AudioMuse finds last run's playlists to replace.
- `DRY_RUN` (1): 1 reports only, 0 removes.
- `SUFFIX`, `ARTIST_FILE`, `LOG_FILE`: only change these if you move things around.

Any of these can also be set on the command line (`sudo MAX_SHARE=0.25 python3 …`), which wins over the file.

### cleanup.env.example

```bash
# Copy to cleanup.env in the same folder, then: chmod 600 cleanup.env

# Navidrome address, and the SAME user AudioMuse uses to create playlists.
# Only a playlist's owner can edit it.
ND_URL=http://10.0.9.101:4533
ND_USER=
ND_PASS=

# Remove listed artists only when they are at most this share of a playlist.
# 0.34 = a third. Above that, the cluster is treated as worship and left alone.
MAX_SHARE=0.34

# Also drop tracks shorter than this many seconds (intros, interludes). 0 = off.
MIN_SECONDS=0

# Put the cluster playlists in a folder, e.g. AudioMuse/Clusters/ (blank = leave names alone).
# The _automatic ending stays, so AudioMuse still replaces them on its next run.
RENAME_PREFIX=

# 1 = report only. Change to 0 once the dry run looks right.
DRY_RUN=1
```

### clean-clusters.py source

```python
#!/usr/bin/env python3
"""clean-clusters.py: take stray worship songs out of AudioMuse clustering playlists.

AudioMuse clusters by sound only, so big guitar worship (Passion, Hillsong UNITED)
lands in alt-rock and skate clusters. This script reads the clustering playlists
in Navidrome (names ending in "_automatic") and removes songs by artists listed in
worship-artists.txt, but only when those songs are a minority of the playlist.
A cluster that is mostly worship is left alone.

  sudo python3 clean-clusters.py            uses DRY_RUN from cleanup.env
  sudo DRY_RUN=1 python3 clean-clusters.py  report only, change nothing
  sudo DRY_RUN=0 python3 clean-clusters.py  remove songs

Safe to run as often as you like: a playlist that is already clean is skipped.
AudioMuse rebuilds these playlists on every clustering run, so schedule this
daily and it tidies each new set within a day.

Settings live in cleanup.env next to this file (see cleanup.env.example).
Uses only the Python standard library, so it runs on the TrueNAS host as is.
"""
import hashlib
import json
import os
import re
import secrets
import sys
import urllib.parse
import urllib.request
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))


def load_env(path):
    vals = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip().strip('"').strip("'")
    vals.update({k: v for k, v in os.environ.items() if k in KEYS})  # command line wins
    return vals


KEYS = {"ND_URL", "ND_USER", "ND_PASS", "MAX_SHARE", "MIN_SECONDS", "DRY_RUN",
        "SUFFIX", "ARTIST_FILE", "LOG_FILE", "RENAME_PREFIX"}
CFG = load_env(os.path.join(HERE, "cleanup.env"))
ND_URL = CFG.get("ND_URL", "http://10.0.9.101:4533").rstrip("/")
ND_USER = CFG.get("ND_USER", "")
ND_PASS = CFG.get("ND_PASS", "")
MAX_SHARE = float(CFG.get("MAX_SHARE", "0.34"))   # remove only if listed songs are at most this share
MIN_SECONDS = int(CFG.get("MIN_SECONDS", "0"))    # also drop tracks shorter than this (intros); 0 = off
DRY_RUN = CFG.get("DRY_RUN", "1") != "0"
SUFFIX = CFG.get("SUFFIX", "_automatic")
ARTIST_FILE = CFG.get("ARTIST_FILE", os.path.join(HERE, "worship-artists.txt"))
LOG_FILE = CFG.get("LOG_FILE", os.path.join(HERE, "clean-clusters.log"))
# Optional folder prefix for the cluster playlists, e.g. "AudioMuse/Clusters/". The "_automatic"
# ending is kept, because AudioMuse finds last run's playlists by that ending to replace them.
RENAME_PREFIX = CFG.get("RENAME_PREFIX", "")

_log_lines = []


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line)
    _log_lines.append(line)


def write_log():
    try:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 1_000_000:
            os.replace(LOG_FILE, LOG_FILE + ".1")  # keep one old log
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write("\n".join(_log_lines) + "\n")
    except OSError as e:
        print(f"WARN  could not write log {LOG_FILE}: {e}")


# --- artist matching ---------------------------------------------------------
def norm(name):
    s = (name or "").lower().replace("&", " and ").replace("+", " and ")
    s = re.sub(r"[^\w\s]", " ", s)          # drop punctuation: "Lofi Hymns." == "lofi hymns"
    return re.sub(r"\s+", " ", s).strip()


SPLIT = re.compile(r"\s*(?:,|;|/|\bfeat\.?|\bft\.?|\bfeaturing\b|\bwith\b|\bx\b|&|\band\b)\s*", re.I)


def credit_names(artist):
    """The full credit plus each name in it, normalized."""
    names = {norm(artist)}
    names.update(norm(p) for p in SPLIT.split(artist or "") if p and p.strip())
    names.discard("")
    return names


def load_artists(path):
    out = set()
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#"):
            out.add(norm(line))
    return out


# --- Subsonic API ------------------------------------------------------------
def api(endpoint, params=None):
    salt = secrets.token_hex(6)
    q = [("u", ND_USER), ("t", hashlib.md5((ND_PASS + salt).encode()).hexdigest()),
         ("s", salt), ("v", "1.16.1"), ("c", "clean-clusters"), ("f", "json")]
    for k, v in (params or []):
        q.append((k, str(v)))
    url = f"{ND_URL}/rest/{endpoint}?{urllib.parse.urlencode(q)}"
    with urllib.request.urlopen(url, timeout=30) as r:
        body = json.load(r)["subsonic-response"]
    if body.get("status") != "ok":
        err = body.get("error", {})
        raise RuntimeError(f"{endpoint}: {err.get('message', 'failed')} (code {err.get('code')})")
    return body


def main():
    if not ND_USER or not ND_PASS:
        print("STOP  set ND_USER and ND_PASS in cleanup.env (the same Navidrome user AudioMuse uses).")
        return 2
    try:
        artists = load_artists(ARTIST_FILE)
    except OSError as e:
        print(f"STOP  can't read artist list {ARTIST_FILE}: {e}")
        return 2

    log(f"{'DRY RUN, nothing will change. ' if DRY_RUN else ''}"
        f"{len(artists)} listed artists, remove when they're at most {MAX_SHARE:.0%} of a playlist"
        + (f", also dropping tracks under {MIN_SECONDS}s" if MIN_SECONDS else ""))
    try:
        api("ping")
        playlists = api("getPlaylists").get("playlists", {}).get("playlist", [])
    except Exception as e:  # network, auth
        log(f"STOP  Navidrome at {ND_URL} is unreachable or refused the login: {e}")
        return 1

    clusters = [p for p in playlists if p.get("name", "").endswith(SUFFIX)]
    log(f"Found {len(clusters)} clustering playlists")
    total_removed = 0

    for p in clusters:
        name, pid = p["name"], p["id"]
        if p.get("owner") and p["owner"] != ND_USER:
            log(f"SKIP  {name}: owned by {p['owner']}, not {ND_USER}. Only the owner can edit it.")
            continue
        songs = api("getPlaylist", [("id", pid)]).get("playlist", {}).get("entry", []) or []
        if not songs:
            continue
        worship = [i for i, s in enumerate(songs) if credit_names(s.get("artist")) & artists]
        share = len(worship) / len(songs)
        if worship and share > MAX_SHARE:
            log(f"KEEP  {name}: {len(worship)}/{len(songs)} songs ({share:.0%}) are listed artists, "
                f"so this is a worship-leaning cluster")
            worship = []
        short = [i for i, s in enumerate(songs)
                 if MIN_SECONDS and 0 < int(s.get("duration") or 0) < MIN_SECONDS]
        drop = sorted(set(worship) | set(short), reverse=True)

        if RENAME_PREFIX and not name.startswith(RENAME_PREFIX):
            new_name = RENAME_PREFIX + name
            log(f"{'WOULD' if DRY_RUN else 'NAME '} {name}  ->  {new_name}")
            if not DRY_RUN:
                api("updatePlaylist", [("playlistId", pid), ("name", new_name)])
            name = new_name

        if not drop:
            continue

        log(f"{'WOULD' if DRY_RUN else 'CLEAN'} {name}: remove {len(drop)} of {len(songs)} songs")
        for i in sorted(drop):
            s = songs[i]
            why = "short" if i in short and i not in worship else "listed artist"
            log(f"        - {s.get('title')} / {s.get('artist')}  ({why})")
        total_removed += len(drop)
        if DRY_RUN:
            continue

        # Remove from the highest index down, one per call, so earlier indexes stay valid.
        for i in drop:
            api("updatePlaylist", [("playlistId", pid), ("songIndexToRemove", i)])
        after = api("getPlaylist", [("id", pid)]).get("playlist", {}).get("entry", []) or []
        if len(after) != len(songs) - len(drop):
            log(f"WARN  {name}: expected {len(songs) - len(drop)} songs after cleanup, found {len(after)}")

    log(f"Done. {'Would remove' if DRY_RUN else 'Removed'} {total_removed} songs. "
        + ("Set DRY_RUN=0 in cleanup.env to apply." if DRY_RUN and total_removed else ""))
    return 0


if __name__ == "__main__":
    code = main()
    write_log()
    sys.exit(code)
```

### worship-artists.txt

228 artists on, plus a review section that's off by default. Delete a `#` to turn a line on.

```text
# Worship artists for clean-clusters.py
#
# Songs by these artists are removed from AudioMuse's _automatic clustering
# playlists, but only when they are a minority of that playlist (MAX_SHARE in
# cleanup.env, default 0.34). A cluster that is mostly worship keeps them.
#
# One artist per line. Case, "&" vs "and", and punctuation don't matter.
# A song matches if its full artist credit, or any one name in it
# ("Elevation Worship & Maverick City Music"), is on this list.
# Lines starting with # are ignored. Delete a # to turn a line on.
#
# Built from your Apple Music worship and hymn playlists (artists that never
# appeared in your rock, punk or alt playlists), the six artists you named,
# and current worship charts and collectives lists.

# --- The six you named -------------------------------------------------------
Passion
Charlie Hall
Hillsong UNITED
Big Tent Revival
The Kry
Ascend the Hill

# --- Worship bands, collectives and church labels ---------------------------
Hillsong Worship
Hillsong Young & Free
Hillsong
Elevation Worship
Elevation Rhythm
Maverick City Music
Bethel Music
Jesus Culture
Planetshakers
Gateway Worship
Vertical Worship
Housefires
UPPERROOM
Red Rocks Worship
River Valley Worship
River Valley AGES
LO Worship
SEU Worship
Sons of Sunday
CityAlight
Shane & Shane
The Worship Initiative
Sovereign Grace Music
North Point Worship
Life.Church Worship
Bethany Music
Influence Music
Kingdom Culture Worship
Victory Worship
New Life Worship
Grace Worship
Transformation Worship
West Coast Revival
Worship Circle
Calvary Creative
Celtic Worship
Isla Vista Worship
The Village Church
Redeemer Christian Church
Red Mountain Church
Reach Church
Project 1:11 Lansing
Frontline Music
Emu Music
Exodus Music
Simply Worship
The Secret Place
Draw Close
All Sons & Daughters
Bryan & Katie Torwalt
Kari Jobe
Kari Jobe Carnes
Cody Carnes
Brandon Lake
Chris Tomlin
Phil Wickham
Matt Redman
Tim Hughes
Martin Smith
Kristian Stanfill
Christy Nockels
Nathan Nockels
Chris Brown
Chandler Moore
Naomi Raine
Pat Barrett
Leeland
Josh Baldwin
Steffany Gretzinger
Jenn Johnson
Brian Johnson
Brian & Jenn Johnson
Jeremy Riddle
Kim Walker-Smith
Bryan McCleery
Tiffany Hudson
Melodie Malone
Brooke Ligertwood
Reuben Morgan
Joel Houston
Taya
Aodhan King
Darlene Zschech
Paul Baloche
Don Moen
Israel Houghton
Michael W. Smith
Lincoln Brewster
Meredith Andrews
Kristene DiMarco
Amanda Cook
Hannah Hobbs
Hope Darst
Mack Brock
Sean Feucht
David Brymer
Aaron Keyes
Aaron Shust
Tommy Walker
Vineyard Worship
Matt Maher
Matt Maher & Friends
Hillsong Kids
Integrity Worship Singers
Maranatha! Music
Maranatha! Praise Band
Passion Worship Band

# --- Hymns, liturgy and acoustic hymn projects ------------------------------
Keith & Kristyn Getty
Getty Music
Stuart Townend
Graham Kendrick
Matt Boswell
Matt Papa
Matt Boswell & Matt Papa
Page CXVI
Page CXVI - Reimagined by Derek Webb
Kings Kaleidoscope Hymns
Hope Hymns
High Street Hymns
Holy City Hymns
City Hymns
Hymns of Grace
Hymns of the People
Indelible Grace Music
Sojourn Music
Cardiphonia Music
Norton Hall Band
The Enfield Hymn Sessions
The Franz Brothers
Brian Sauve
Bob Kauflin
Dave Hunt
A New Liturgy
Greg Attwells
Providence
Salt of the Sound
Fernando Ortega
Thief to King
Dear Gravity
Daniel Martin Moore
Adam Wheatley
The Journey Collective
Ken Verheecke
My Soul Among Lions
Servants
Sojourners
She Reads Truth
The Gospel Coalition
Fount
Nathan Clark George
Gregory Wilbur
Redeemer Presbyterian Church
Asaph's Arrows
The Lower Lights
Wilder Adkins
Paul Zach
Nathan Drake
Christopher Galovan
Chris Rice
John Ofa Rhee
Alabaster Co.
Simon Wester

# --- Instrumental, piano and lofi worship -----------------------------------
The Lofi Christian
Lofi Worship
Lofi Hymns.
Pathway Piano
Piano Praises
Carl Eksmo
Tony Anderson
Dan Musselman
Stian Jarrell
Jim Brickman
Adam Zampino
Michele McLaughlin
Manuel Elastic
Sarah Brooks
Joshua David Harris
Khamir Music
Huckleberry Flint
Kendra Logozar
Michael Logozar
Eric Gilmour

# --- CCM adult contemporary (the Big Tent Revival / The Kry kind) ------------
MercyMe
Casting Crowns
Steven Curtis Chapman
Twila Paris
Point of Grace
Avalon
Natalie Grant
Jason Gray
Sanctus Real
Tenth Avenue North
Building 429
Big Daddy Weave
Matthew West
Mark Schultz
Jaci Velasquez
Rebecca St. James
Nichole Nordeman
Bebo Norman
Phillips, Craig & Dean
4Him
Margaret Becker
Rich Mullins
Ginny Owens
Out of Eden
Zoegirl
BarlowGirl
Sara Groves
Danny Gokey
Lauren Daigle
Zach Williams
Jeremy Camp
Unspoken
Jordan Feliz
Cain
Anne Wilson
Josh Wilson
Francesca Battistelli
Selah
Sidewalk Prophets
Hawk Nelson

# --- Review: gray area, OFF by default ---------------------------------------
# These are worship or CCM artists that also show up a lot in your rock,
# indie and youth group playlists. Delete the # to treat them as worship too.
# Crowder
# David Crowder Band
# Kings Kaleidoscope
# Citizens
# Citizens & Saints
# Chris Renzema
# John Mark Pantana
# Rivers & Robots
# Rend Collective
# Josh Garrels
# Third Day
# Delirious?
# Newsboys
# TobyMac
# Audio Adrenaline
# Jars of Clay
# Forrest Frank
# Josiah Queen
# We The Kingdom
# for KING & COUNTRY
# Tauren Wells
# Hulvey
# Local Sound
```

## navidrome.env

Shared by `tag-tidarr-playlists.py` and `rename-playlists.py`. The user must own the playlists or be a Navidrome admin, so use your own admin account.

```bash
sudo mkdir -p /mnt/ssd-pool/apps/navidrome/scripts
sudo tee /mnt/ssd-pool/apps/navidrome/scripts/navidrome.env >/dev/null <<'EOF'
ND_URL=http://10.0.9.101:4533
ND_USER=mikestecker
ND_PASS=your-navidrome-password
EOF
sudo chown root:root /mnt/ssd-pool/apps/navidrome/scripts/navidrome.env
sudo chmod 600 /mnt/ssd-pool/apps/navidrome/scripts/navidrome.env
```

## tag-tidarr-playlists.py

Tidarr writes its `.m3u` playlists into `/music/m3u/playlist/`, and Navidrome imports them with plain names. This finds every playlist whose file path contains `/m3u/playlist/`, adds the `Imports/Tidarr/` prefix and sets the comment to `Tidarr import: <file>`. Only the name inside Navidrome changes, so Tidarr can keep updating the files, and Navidrome keeps the new name when it re-reads them. You don't need to add Tidarr playlists to `playlist-folders.txt`; this handles all of them.

```bash
cd /mnt/ssd-pool/apps/navidrome/scripts
sudo python3 tag-tidarr-playlists.py                       # report only
sudo python3 tag-tidarr-playlists.py --apply               # rename and tag
sudo python3 tag-tidarr-playlists.py --undo --apply        # take the prefix off again
sudo python3 tag-tidarr-playlists.py --undo --prefix "📥 " --apply   # remove an old emoji prefix
```

New Tidarr playlists show up with plain names until the next run, which is why the daily cron job (06:15) is worth adding.

```python
#!/usr/bin/env python3
"""tag-tidarr-playlists.py: mark the playlists Navidrome imported from Tidarr's .m3u files.

Navidrome has no playlist folders, so this files every playlist that came from
Tidarr's m3u folder under a name prefix (default "Imports/Tidarr/", the folder
convention Feishin shows as folders) and sets its comment to "Tidarr import: <file>".
That groups them in every client and makes them easy to find and remove later.

Only the name inside Navidrome changes. The .m3u files stay as they are, so Tidarr
can keep updating them, and Navidrome keeps a playlist's name when it re-reads its
file. New Tidarr playlists show up with plain names until the next run, so it's
safe to schedule daily.

  sudo python3 tag-tidarr-playlists.py            report only
  sudo python3 tag-tidarr-playlists.py --apply    rename and tag
  sudo python3 tag-tidarr-playlists.py --undo --apply   take the prefix off again
  sudo python3 tag-tidarr-playlists.py --undo --prefix "📥 " --apply   remove the old emoji prefix

Settings: navidrome.env next to this file (ND_URL, ND_USER, ND_PASS). The user must
own the playlists or be a Navidrome admin.
"""
import argparse
import hashlib
import json
import os
import secrets
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def load_env(path):
    vals = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("ND_URL", "ND_USER", "ND_PASS"):
        if os.environ.get(k):
            vals[k] = os.environ[k]
    return vals


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--env", default=os.path.join(HERE, "navidrome.env"))
    ap.add_argument("--prefix", default="Imports/Tidarr/", help='prefix to add (default "Imports/Tidarr/")')
    ap.add_argument("--path-match", default="/m3u/playlist/",
                    help="playlists whose file path contains this are Tidarr imports")
    ap.add_argument("--apply", action="store_true", help="make the changes (default is a dry run)")
    ap.add_argument("--undo", action="store_true", help="remove the prefix and comment instead")
    a = ap.parse_args()

    cfg = load_env(a.env)
    url = cfg.get("ND_URL", "http://10.0.9.101:4533").rstrip("/")
    user, pw = cfg.get("ND_USER", ""), cfg.get("ND_PASS", "")
    if not user or not pw:
        print(f"STOP  set ND_URL, ND_USER and ND_PASS in {a.env}")
        return 2

    # Navidrome's own API is the only one that says which file a playlist came from.
    try:
        req = urllib.request.Request(f"{url}/auth/login", method="POST",
                                     data=json.dumps({"username": user, "password": pw}).encode(),
                                     headers={"Content-Type": "application/json"})
        token = json.load(urllib.request.urlopen(req, timeout=30)).get("token")
        if not token:
            raise RuntimeError("login refused, check ND_USER and ND_PASS")
        req = urllib.request.Request(f"{url}/api/playlist?_start=0&_end=10000&_sort=name&_order=ASC",
                                     headers={"X-ND-Authorization": f"Bearer {token}"})
        playlists = json.load(urllib.request.urlopen(req, timeout=60))
    except Exception as e:
        print(f"STOP  couldn't log in to Navidrome at {url} or list playlists: {e}")
        return 1

    def subsonic(endpoint, params):
        salt = secrets.token_hex(6)
        q = [("u", user), ("t", hashlib.md5((pw + salt).encode()).hexdigest()), ("s", salt),
             ("v", "1.16.1"), ("c", "tag-tidarr"), ("f", "json")] + params
        with urllib.request.urlopen(f"{url}/rest/{endpoint}?{urllib.parse.urlencode(q)}", timeout=30) as r:
            body = json.load(r)["subsonic-response"]
        if body.get("status") != "ok":
            raise RuntimeError(body.get("error", {}).get("message", "failed"))

    tidarr = [p for p in playlists if a.path_match in (p.get("path") or "")]
    print(f"{'' if a.apply else 'DRY RUN, nothing will change. '}"
          f"{len(tidarr)} of {len(playlists)} playlists came from Tidarr ({a.path_match}).")

    changed = 0
    for p in tidarr:
        name, fname = p["name"], os.path.basename(p["path"])
        tag = f"Tidarr import: {fname}"
        if a.undo:
            if not name.startswith(a.prefix):
                continue
            new_name, new_comment = name[len(a.prefix):], ""
        else:
            if name.startswith(a.prefix) and (p.get("comment") or "") == tag:
                continue
            new_name = name if name.startswith(a.prefix) else a.prefix + name
            new_comment = tag
        print(f"  {'RENAME' if a.apply else 'WOULD '}  {name}  ->  {new_name}")
        changed += 1
        if a.apply:
            try:
                subsonic("updatePlaylist", [("playlistId", p["id"]), ("name", new_name), ("comment", new_comment)])
            except Exception as e:
                print(f"  FAIL    {name}: {e}")
    print(f"Done. {'Changed' if a.apply else 'Would change'} {changed}."
          + (" Run again with --apply to make the changes." if changed and not a.apply else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## rename-playlists.py

Renames playlists into folders (`Folder/Subfolder/Playlist`) from a plain-text map, so the map is your source of truth for how things are organized. The folder convention itself is in the Organizing playlists tab. Renames stick even for playlists that come from `.m3u` or `.nsp` files.

```bash
cd /mnt/ssd-pool/apps/navidrome/scripts
sudo python3 rename-playlists.py --list      # every current playlist name, to build the map from
sudo nano playlist-folders.txt                # add or edit rules
sudo python3 rename-playlists.py              # report only
sudo python3 rename-playlists.py --apply      # rename
```

It skips a rename if a playlist with the new name already exists, and warns about playlists owned by someone else. Rules for playlists you don't have are ignored, so the map can run ahead of your library.

```python
#!/usr/bin/env python3
"""rename-playlists.py: file Navidrome playlists into folders by renaming them.

Navidrome has no playlist folders yet. Until it does, the convention is a slash path
in the name, "Folder/Subfolder/Playlist", which Feishin can show as folders and which
sorts together in every other app. This script renames playlists from a plain text map,
so you can (re)organize everything in one go and keep the map as your source of truth.

  sudo python3 rename-playlists.py              report only
  sudo python3 rename-playlists.py --apply      rename
  sudo python3 rename-playlists.py --list       print every playlist name, to start a map

Map file (default: playlist-folders.txt next to this file), one rule per line:
  Recently Added => Smart/Recently Added
  🤖 Sonic Fingerprint => AudioMuse/Sonic Fingerprint
  prefix: 📥  => Imports/Tidarr/          (swap a leading prefix on every playlist that has it)
Lines starting with # are ignored. Names match exactly, ignoring case and outer spaces.

Settings: navidrome.env next to this file (ND_URL, ND_USER, ND_PASS). The user must own
the playlists or be a Navidrome admin. Navidrome keeps a renamed name even for playlists
that come from .m3u or .nsp files, so renames stick.
"""
import argparse
import hashlib
import json
import os
import secrets
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def load_env(path):
    vals = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("ND_URL", "ND_USER", "ND_PASS"):
        if os.environ.get(k):
            vals[k] = os.environ[k]
    return vals


def load_map(path):
    exact, prefixes = {}, []
    for n, raw in enumerate(open(path, encoding="utf-8"), 1):
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "=>" not in line:
            print(f"WARN  line {n} has no '=>', skipped: {line}")
            continue
        old, new = line.split("=>", 1)
        if old.strip().lower().startswith("prefix:"):
            # keep the old prefix exactly (an emoji prefix includes its trailing space)
            prefixes.append((old.split(":", 1)[1].lstrip(), new.lstrip()))
        else:
            exact[old.strip().lower()] = new.strip()
    return exact, prefixes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--env", default=os.path.join(HERE, "navidrome.env"))
    ap.add_argument("--map", default=os.path.join(HERE, "playlist-folders.txt"))
    ap.add_argument("--apply", action="store_true", help="rename (default is a dry run)")
    ap.add_argument("--list", action="store_true", help="print all playlist names and exit")
    a = ap.parse_args()

    cfg = load_env(a.env)
    url = cfg.get("ND_URL", "http://10.0.9.101:4533").rstrip("/")
    user, pw = cfg.get("ND_USER", ""), cfg.get("ND_PASS", "")
    if not user or not pw:
        print(f"STOP  set ND_URL, ND_USER and ND_PASS in {a.env}")
        return 2

    def api(endpoint, params=()):
        salt = secrets.token_hex(6)
        q = [("u", user), ("t", hashlib.md5((pw + salt).encode()).hexdigest()), ("s", salt),
             ("v", "1.16.1"), ("c", "rename-playlists"), ("f", "json")] + list(params)
        with urllib.request.urlopen(f"{url}/rest/{endpoint}?{urllib.parse.urlencode(q)}", timeout=30) as r:
            body = json.load(r)["subsonic-response"]
        if body.get("status") != "ok":
            raise RuntimeError(body.get("error", {}).get("message", "failed"))
        return body

    try:
        playlists = api("getPlaylists").get("playlists", {}).get("playlist", [])
    except Exception as e:
        print(f"STOP  Navidrome at {url} is unreachable or refused the login: {e}")
        return 1

    if a.list:
        for p in sorted(playlists, key=lambda p: p["name"].lower()):
            print(p["name"])
        return 0

    try:
        exact, prefixes = load_map(a.map)
    except OSError as e:
        print(f"STOP  can't read map file {a.map}: {e}")
        return 2

    print(f"{'' if a.apply else 'DRY RUN, nothing will change. '}{len(playlists)} playlists, "
          f"{len(exact)} name rules, {len(prefixes)} prefix rules.")
    taken = {p["name"].lower() for p in playlists}
    changed = 0
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
            print(f"  SKIP    {name}  ->  {new}  (a playlist with that name already exists)")
            continue
        if p.get("owner") and p["owner"] != user:
            print(f"  NOTE    {name} is owned by {p['owner']}; this only works if {user} is an admin")
        print(f"  {'RENAME' if a.apply else 'WOULD '}  {name}  ->  {new}")
        changed += 1
        if a.apply:
            try:
                api("updatePlaylist", [("playlistId", p["id"]), ("name", new)])
                taken.discard(name.lower()); taken.add(new.lower())
            except Exception as e:
                print(f"  FAIL    {name}: {e}")
    print(f"Done. {'Renamed' if a.apply else 'Would rename'} {changed}."
          + (" Run again with --apply to make the changes." if changed and not a.apply else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### playlist-folders.txt

```text
# playlist-folders.txt: where each playlist lives. Used by rename-playlists.py.
#
#   Old name => Folder/Subfolder/New name
#   prefix: Old prefix => New/prefix/        (applies to every playlist starting with it)
#
# Names match exactly, ignoring case. A rule for a playlist you don't have is ignored.
# Two levels deep at most: Feishin's folder view groups by the part before each "/".
# Run "sudo python3 rename-playlists.py --list" to see every current name.

# --- Smart playlists (.nsp files) --------------------------------------------
Recently Added => Smart/Recently Added
Recently Played => Smart/Recently Played
Top 25 Most Played => Smart/Top 25 Most Played
Favorites => Smart/Favorites
Forgotten Favorites => Smart/Forgotten Favorites
90s Music => Smart/90s Music
Christmas Songs => Smart/Christmas Songs
dc Talk => Smart/Artists/dc Talk
Jars of Clay => Smart/Artists/Jars of Clay
Jon Foreman => Smart/Artists/Jon Foreman
Blindside => Smart/Artists/Blindside
Muse => Smart/Artists/Muse
Mute Math => Smart/Artists/Mute Math
MxPx => Smart/Artists/MxPx
NEEDTOBREATHE => Smart/Artists/NEEDTOBREATHE
P.O.D. => Smart/Artists/P.O.D.
Project 86 => Smart/Artists/Project 86
Radiohead => Smart/Artists/Radiohead
Skillet => Smart/Artists/Skillet
Smashing Pumpkins => Smart/Artists/Smashing Pumpkins
The Beatles => Smart/Artists/The Beatles
Thrice => Smart/Artists/Thrice
U2 => Smart/Artists/U2

# --- AudioMuse's fixed playlists ---------------------------------------------
# Also change these names in AudioMuse (Setup Wizard) so it keeps updating the same playlist.
🤖 Sonic Fingerprint => AudioMuse/Sonic Fingerprint
🤖 Album of the Week => AudioMuse/Album of the Week

# --- Your saved runs and keepers (examples; edit to match your real names) --------
# Pool Day => Occasions/Summer/Pool Day
# Classic Rock BBQ => Occasions/Parties/Classic Rock BBQ
# Christian Hip-Hop Workout => Occasions/Workouts/Christian Hip-Hop Workout
# Pickleball => Occasions/Workouts/Pickleball
# Sunday Morning Worship => Faith/Worship/Sunday Morning Worship
# Modern Hymns => Faith/Hymns/Modern Hymns
# Youth Group Throwback => Faith/Christian Rock/Youth Group Throwback
# Country Bedroom Slow Jams => Moods/Date Night/Country Bedroom Slow Jams
# 90s Alt Throwback => Eras/90s/90s Alt Throwback
# Classic Christmas => Seasonal/Christmas/Classic Christmas
# Office Party 2025 => Curated/Events/Office Party 2025
```

## fix-m3u-paths.py

When albums were re-downloaded from Tidal, some files changed name, extension or folder, and the `.m3u` playlists still point at the old paths. Navidrome logs `Path in playlist not found` and silently drops those songs. This finds each missing entry's song in your library by artist folder and track title (ignoring track numbers, extension, year and edition words), and rewrites the line in the same style it was written in. Each changed playlist gets a `.bak-<time>` copy first, and the file keeps its owner.

```bash
sudo python3 /mnt/ssd-pool/apps/navidrome/scripts/fix-m3u-paths.py           # report only
sudo python3 /mnt/ssd-pool/apps/navidrome/scripts/fix-m3u-paths.py --apply   # rewrite (backups kept)
```

Defaults match your NAS: `--music /mnt/tank/media/music`, `--playlists <music>/m3u/playlist`, `--container-root /music`. No rescan needed afterwards; Navidrome's folder watcher picks up the changed files. Once you're happy, clear the backups with `sudo find /mnt/tank/media/music/m3u/playlist -name '*.bak-*' -delete`.

```python
#!/usr/bin/env python3
"""fix-m3u-paths.py: repoint .m3u playlist entries at the files you have now.

When albums were re-downloaded from Tidal, some files changed name, extension or
folder (".m4a" became ".flac", "Crash My Party (2023)" became another edition...).
The .m3u playlists still point at the old paths, so Navidrome logs
"Path in playlist not found" and silently drops those songs.

For every entry that no longer exists, this finds the same song in your library by
artist folder and track title (ignoring track numbers, extension, year and edition
words), and rewrites the line in the same style it was written in.

  sudo python3 fix-m3u-paths.py            report only, change nothing
  sudo python3 fix-m3u-paths.py --apply    rewrite the playlists (backups kept)

Uses only the Python standard library, so it runs on the TrueNAS host as is.
"""
import argparse
import os
import re
import shutil
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime

AUDIO = {".flac", ".m4a", ".mp3", ".alac", ".aac", ".ogg", ".opus", ".wav", ".aiff", ".aif", ".wma", ".dsf"}
EDITION = re.compile(r"\b(deluxe|expanded|edition|remaster(ed)?|anniversary|special|version|bonus|explicit|clean)\b", re.I)


def compact(s):
    """Lowercase letters and digits only: 'half·alive' == 'Half Alive', 'Needtobreathe' == 'NEEDTOBREATHE'."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower().replace("&", "and"))


def title_key(filename):
    """'06 Fight For Me.m4a' / '1-06 - Fight For Me (feat. X).flac' -> 'fightforme'."""
    stem = os.path.splitext(os.path.basename(filename))[0]
    stem = re.sub(r"^\s*(\d{1,2}[-.])?\d{1,3}\s*[-._]?\s+", "", stem)        # track / disc numbers
    stem = re.sub(r"\s*[\(\[](feat|ft|with)\.?[^\)\]]*[\)\]]", "", stem, flags=re.I)
    return compact(stem)


def track_no(filename):
    m = re.match(r"^\s*(?:\d{1,2}[-.])?(\d{1,3})\b", os.path.basename(filename))
    return int(m.group(1)) if m else None


def album_key(folder):
    folder = re.sub(r"[\(\[]\s*\d{4}\s*[\)\]]", "", folder)                     # (2018)
    folder = re.sub(r"[\(\[][^\)\]]*[\)\]]", lambda m: "" if EDITION.search(m.group(0)) else m.group(0), folder)
    return compact(folder)


def index_library(root, skip):
    """title_key -> list of (relative path, artist_key, album_key, track_no)."""
    idx = defaultdict(list)
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if os.path.join(dirpath, d) not in skip and not d.startswith(".")]
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
    """Best current file for an old library-relative path, or (None, reason)."""
    parts = old_rel.replace("\\", "/").split("/")
    artist = compact(parts[0]) if len(parts) > 1 else ""
    album = album_key(parts[-2]) if len(parts) > 2 else ""
    tkey, tno = title_key(parts[-1]), track_no(parts[-1])
    cands = [c for c in idx.get(tkey, []) if not artist or c[1] == artist]
    if not cands and artist:
        # artist folder renamed more than case/punctuation: accept if the title is unique in the library
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--music", default="/mnt/tank/media/music", help="library root on the NAS")
    ap.add_argument("--playlists", default=None, help="folder of .m3u files (default: <music>/m3u/playlist)")
    ap.add_argument("--container-root", default="/music", help="where Navidrome sees the library")
    ap.add_argument("--apply", action="store_true", help="rewrite the playlists (default is a dry run)")
    a = ap.parse_args()
    music = a.music.rstrip("/")
    pl_dir = a.playlists or os.path.join(music, "m3u", "playlist")
    croot = a.container_root.rstrip("/")

    if not os.path.isdir(music) or not os.path.isdir(pl_dir):
        print(f"STOP  can't find {music} or {pl_dir}. Pass --music / --playlists.")
        return 2

    print(f"{'' if a.apply else 'DRY RUN, nothing will change. '}Indexing {music} ...")
    idx, n = index_library(music, skip={pl_dir, os.path.join(music, "_playlists")})
    print(f"Indexed {n} audio files.\n")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    tot_fixed = tot_missing = tot_files = 0

    for name in sorted(os.listdir(pl_dir)):
        if not name.lower().endswith((".m3u", ".m3u8")):
            continue
        path = os.path.join(pl_dir, name)
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
            entry = re.sub(r"^\d+:(?=[^/\\])", "", entry)   # Navidrome's "1:" library prefix, if present
            # work out where it points and how it was written
            if entry.startswith(croot + "/"):
                style, rel = "container", entry[len(croot) + 1:]
            elif entry.startswith(music + "/"):
                style, rel = "host", entry[len(music) + 1:]
            elif os.path.isabs(entry):
                out.append(line); misses.append((entry, "outside the library")); continue
            else:
                beside = os.path.normpath(os.path.join(pl_dir, entry))
                if beside.startswith(music + "/") and os.path.exists(beside):
                    out.append(line); continue
                if os.path.exists(os.path.join(music, entry)):
                    out.append(line); continue
                # relative to the playlist folder if it climbs out with ../, else relative to the library
                if entry.startswith(".."):
                    style, rel = "relative", os.path.relpath(beside, music)
                else:
                    style, rel = "library", entry
            if os.path.exists(os.path.join(music, rel)):
                out.append(line)
                continue

            new_rel, note = find_match(rel, idx)
            if not new_rel:
                out.append(line); misses.append((rel, note)); continue
            if style == "container":
                new = f"{croot}/{new_rel}"
            elif style == "host":
                new = f"{music}/{new_rel}"
            elif style == "relative":
                new = os.path.relpath(os.path.join(music, new_rel), pl_dir)
            else:
                new = new_rel
            out.append(new)
            fixes.append((rel, new_rel, note))

        if not fixes and not misses:
            continue
        tot_files += 1
        print(f"{name}: {len(fixes)} fixed, {len(misses)} still missing")
        for old, new, note in fixes:
            print(f"   FIX   {old}\n      -> {new}   ({note})")
        for old, why in misses:
            print(f"   MISS  {old}   ({why})")
        tot_fixed += len(fixes)
        tot_missing += len(misses)

        if a.apply and fixes:
            st = os.stat(path)
            shutil.copy2(path, f"{path}.bak-{stamp}")
            data = nl.join(out)
            with open(path, "w", encoding="utf-8-sig" if bom else "utf-8", newline="") as f:
                f.write(data)
            os.chown(path, st.st_uid, st.st_gid)

    print(f"\n{tot_files} playlists with broken entries. "
          f"{'Fixed' if a.apply else 'Can fix'} {tot_fixed}, {tot_missing} have no match in the library.")
    if not a.apply and tot_fixed:
        print("Run again with --apply to rewrite them. Each changed playlist gets a .bak copy first.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## Credentials and security

- `cleanup.env` and `navidrome.env` hold Navidrome passwords. Keep them `root:root` and `chmod 600`, which is why every command here uses `sudo` (including `sudo grep`).
- The plugin settings snapshots in `plugin-backups/` can hold the ListenBrainz and AudioMuse tokens. The update script writes them root-only.
- If a password or token ever ends up in a chat, a screenshot or a log, change it. The ListenBrainz token from earlier is worth resetting if you haven't already.
