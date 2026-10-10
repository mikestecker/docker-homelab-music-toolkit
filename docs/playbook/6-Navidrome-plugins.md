# Navidrome plugins

Moved here from the separate Navidrome Plugin Stack doc (Oct 7).

## At a glance

Five plugins make the cut out of roughly 35 repos tagged `navidrome-plugin` on GitHub. Together they give Navidrome sonic radio, lyrics in every client, better artist pages and Spotify-style personal mixes. The fifth adds ListenBrainz's Daily and Weekly Jams once you have a ListenBrainz account. All five install the same way and are kept current by one script (see Updating).

| Plugin | What it adds | Plugin ID | Version (Oct 7) |
| --- | --- | --- | --- |
| [AudioMuse-AI](https://github.com/NeptuneHub/AudioMuse-AI-NV-plugin) | Instant Mix, artist radio and similar artists from AudioMuse's sonic analysis | `audiomuseai` | 10.0.0 |
| [Lyrics](https://github.com/J0R6IT0/navidrome-lyrics-plugin) (J0R6IT0) | Synced and plain lyrics from LRCLIB, lrcmux (Musixmatch, Genius) and others, for tracks without embedded lyrics | `nd-lyrics` | 8.1.0 |
| [Apple Music Metadata](https://github.com/navidrome/apple-music-plugin) (official) | Current artist photos, bios, top songs and album notes, no API key | `apple-music` | 0.2.0 |
| [NaviBeat Mixes](https://github.com/nenadjokic/navibeat-mixes) | Personal mixes from your listening: Rediscover, On Repeat, Weekly Discovery, New Music | `navibeat-mixes` | 0.9.17 |
| [ListenBrainz Daily Playlist](https://github.com/kgarner7/navidrome-listenbrainz-daily-playlist) | Imports ListenBrainz's Daily Jams and Weekly Jams, limited to tracks you own | `listenbrainz-daily-playlist` | 6.0.0 |

The plugin ID is the `.ndp` file name without the extension. It's the name used in `ND_AGENTS`, `ND_LYRICSPRIORITY` and the `navidrome plugin` commands, so don't rename the files.

Requirements: Navidrome 0.63.1 or newer (NaviBeat's floor; Lyrics needs 0.63.0). Check with `sudo docker exec navidrome navidrome --version`.

## Navidrome compose changes

Add the four plugin lines to the existing `navidrome` service and leave the rest as is. Redeploy once before installing anything, so the plugin system is on.

```yaml
  navidrome:
    container_name: navidrome
    environment:
      - ND_LASTFM_ENABLED=true
      - ND_LASTFM_APIKEY=KEY_HERE
      - ND_LASTFM_SECRET=SECRET_HERE
      - ND_PLUGINS_ENABLED=true
      - ND_PLUGINS_AUTORELOAD=true
      - ND_AGENTS=audiomuseai,apple-music,lastfm,deezer
      - ND_LYRICSPRIORITY=.lrc,.txt,embedded,nd-lyrics
    image: deluan/navidrome:latest
    ports:
      - '4533:4533'
    restart: unless-stopped
    user: '3000:3000'
    volumes:
      - /mnt/ssd-pool/apps/navidrome:/data
      - /mnt/tank/media/music:/music:ro
      - /mnt/tank/media/downloads/aurral:/data/downloads/aurral:ro
```

- **`ND_AGENTS` order matters.** Navidrome asks agents in order. `audiomuseai` first means AudioMuse answers Instant Mix and similar artists. Apple Music then supplies photos, bios and top songs, and Last.fm and Deezer fill whatever is left.
- **`ND_LYRICSPRIORITY`** uses `.lrc`/`.txt` sidecars and Tidarr's embedded lyrics first. The plugin only goes online for tracks with neither.
- **Music stays read-only.** None of these plugins needs to write to the library, so keep `:ro`.
- Plugins live in `/mnt/ssd-pool/apps/navidrome/plugins` on the host (`/data/plugins` in the container). Navidrome creates it on first start with `ND_PLUGINS_ENABLED=true`.

## Install

Run this from the TrueNAS shell. It downloads all five `.ndp` files from each project's latest GitHub release, sets ownership to the `svc_apps` user (3000:3000), and has Navidrome pick them up. All five URLs were checked on Oct 7.

```bash
P=/mnt/ssd-pool/apps/navidrome/plugins
sudo mkdir -p "$P"

sudo curl -fL -o "$P/audiomuseai.ndp"                 https://github.com/NeptuneHub/AudioMuse-AI-NV-plugin/releases/latest/download/audiomuseai.ndp
sudo curl -fL -o "$P/nd-lyrics.ndp"                   https://github.com/J0R6IT0/navidrome-lyrics-plugin/releases/latest/download/nd-lyrics.ndp
sudo curl -fL -o "$P/apple-music.ndp"                 https://github.com/navidrome/apple-music-plugin/releases/latest/download/apple-music.ndp
sudo curl -fL -o "$P/navibeat-mixes.ndp"              https://github.com/nenadjokic/navibeat-mixes/releases/latest/download/navibeat-mixes.ndp
sudo curl -fL -o "$P/listenbrainz-daily-playlist.ndp" https://github.com/kgarner7/navidrome-listenbrainz-daily-playlist/releases/latest/download/listenbrainz-daily-playlist.ndp

sudo chown -R 3000:3000 "$P"
sudo docker exec navidrome navidrome plugin rescan
sudo docker exec navidrome navidrome plugin list
```

`plugin list` should show all five as disabled. That's expected: Navidrome adds every new plugin switched off until you configure it in the UI (next section).

The update script below does the same download, so you can install with it instead: run it once and it reports each plugin as `ADD`.

## Per-plugin setup

Everything here is in Navidrome under **Settings → Plugins**. Open each plugin, set the fields, save, then flip it to **Enabled**. You only do this once: updates keep these settings.

Three plugins won't enable until you make an access choice on their page. Lyrics asks which **libraries** it may see, NaviBeat asks which **users** it acts for, and ListenBrainz asks for both. Navidrome refuses to turn them on until that's set.

### AudioMuse-AI

- **AudioMuse-AI API URL:** `http://10.0.9.101:8000`. Navidrome and AudioMuse are separate compose stacks on separate networks, so use the host IP, not a container name.
- **API Token:** the token from AudioMuse's Setup Wizard. AudioMuse has auth on by default, and a blank or wrong token shows up as a 401 in the Navidrome log.
- **Server Name:** blank. You only have one media server in AudioMuse.
- **Instant Mix Functionality:** Similar Song.
- Wait until AudioMuse's first analysis finishes before you test. Instant Mix needs the index that gets built at the end of the run.
- **Test it:** run Similar Song on a track in AudioMuse, then Instant Mix on the same track in Navidrome. Both should show up in `sudo docker logs audiomuse-flask`.

### Lyrics (nd-lyrics)

- **Libraries:** select your music library.
- **Lyrics providers:** `lrclib`, then `lrcmux`, then `lyrics.ovh`. The default is just LRCLIB and lyrics.ovh. lrcmux adds Musixmatch, Genius and NetEase as fallbacks.
- **Provider mode:** Priority.
- **Write lyrics to sidecar files:** off. Your music mount is read-only, and Tidarr already embeds lyrics.
- Leave the caching defaults: 7 days for hits, 24 hours for misses.
- The Navidrome web UI doesn't show lyrics that come from plugins yet. Check them in Feishin or Symfonium instead.

### Apple Music Metadata

- **Countries:** `us`.
- **Album Images:** leave it off. Picard and Tidarr embed cover art, and Navidrome uses local art before asking any agent.
- Leave everything else on. Similar Artists only comes into play when AudioMuse has no answer, because it sits ahead of Apple Music in `ND_AGENTS`.
- To see the difference, open an artist page. Photos and bios that came from Last.fm before now come from Apple Music.

### NaviBeat Mixes

- **Users:** select your own account. The family listens through Plexamp, so their Navidrome history would be empty anyway.
- **Build mixes only for these accounts:** your Navidrome username.
- **Mixes to keep on:** Rediscover, On Repeat, Weekly Discovery, New Music, Your Loved Songs.
- **Mixes to turn off for now:**
  - Artist Radio and Genre Radio overlap with AudioMuse.
  - Daily Mix 1–3 and Decade are optional. Add them later if you want more.
  - Morning, Afternoon, Evening and Night only mean something after about 150 plays through Navidrome. Turn them on once you've used Feishin for a few weeks.
- **New Music: what counts as new:** `released`. You're still backfilling older albums, so going by date added would fill New Music with old records.
- **Share Wrapped:** leave it off. That's the only setting that sends anything off your server.
- **Playlist name prefix:** the default is an orange-dot emoji. Change it to something like ` NB ·  ` if you'd rather not have emoji in your playlist names.
- Mixes appear within a minute of enabling the plugin and refresh at 04:00 every day.

### ListenBrainz Daily Playlist

This one needs a ListenBrainz account and some history first, so set it up last. It's worth adding: the plugin is mature (v6.0.0, maintained since July 2025), and your library is already MusicBrainz-tagged, which is the hard part for most people.

**ListenBrainz side (one time):**

1. Create an account at [listenbrainz.org](https://listenbrainz.org). It uses a MusicBrainz login.
2. Import your Last.fm history from [listenbrainz.org/import-data](https://listenbrainz.org/import-data/). Recommendations come from your history, so this gets you years of it instead of starting from zero.
3. Follow the user [troi-bot](https://listenbrainz.org/user/troi-bot/). The Daily Jams playlist is only generated for people who follow it.
4. Copy your user token from your ListenBrainz settings.
5. In Navidrome, open your user menu → **Personal** and switch on **Scrobble to ListenBrainz** with that token. Keep Last.fm on as well; Navidrome scrobbles to both.
6. Wait for the first playlists. Weekly playlists are generated on Monday mornings.

**Plugin settings:**

- **Users and libraries:** your account and your music library.
- **User configurations:** add one entry with your Navidrome username, your ListenBrainz username and your token.
- **Playlists to import:**
  - Source `daily-jams`, named `LB Daily Jams`.
  - Source `weekly-jams`, named `LB Weekly Jams`.
- **Skip `weekly-exploration`.** It's built from music you mostly don't own, and the plugin only adds tracks already in your library, so it would come out nearly empty. Use Aurral for finding new music.
- **Generate playlist:** off. It's marked experimental, and its own README warns it can make 1000+ requests per run.
- **Hour to fetch playlists:** `7`.

**Matching:** the plugin matches tracks by MusicBrainz recording ID only. Anything Lidarr imported, or that went through your Picard tag-only pass, will match. Tidarr downloads that haven't been through Picard yet won't, so short playlists usually mean those albums need tagging.

**Ongoing listens:** Navidrome only sends ListenBrainz the plays that go through Navidrome. Plexamp, Tidal and Rockbox plays reach Last.fm but not ListenBrainz. Check whether the import page can keep pulling from Last.fm automatically. If it can't, rerun the import every so often so your recommendations keep up.

## Updating

Updates take one command, run weekly from a TrueNAS cron job. The script downloads each plugin's latest release and leaves any that haven't changed alone. It swaps in new versions, re-enables them, and restarts Navidrome only if something actually changed.

**Why it needs more than a file copy.** Navidrome fingerprints every `.ndp`. When a file changes, it marks that plugin *disabled*, because a new version might ask for new permissions. I confirmed this in Navidrome's source (`plugins/manager_sync.go`). Your settings, users and libraries are kept, but the plugin stays off until someone turns it back on. Navidrome's built-in `plugin` CLI fixes that without the UI:

1. Download the new `.ndp`, check it's a real plugin package, and keep a backup of the old one.
2. `navidrome plugin rescan` records the new version.
3. `navidrome plugin enable <id>`, only for the plugins that were updated.
4. `docker restart navidrome` so the running server loads them.

Plugins installed for the first time are added but not enabled, since they need the one-time setup above.

**Settings safety net (added Oct 7).** The first manual run wiped NaviBeat's settings. Navidrome's own code (v0.64.2) is supposed to keep them, so the cause isn't confirmed yet. The script no longer relies on that:

- Before it changes anything, it saves every plugin's settings, users and libraries to `plugin-backups/plugin-settings-<time>.json`. It keeps the last 10.
- After each update, it compares the updated plugins against that snapshot and puts back anything that changed, using `navidrome plugin edit`.
- It checks again 20 seconds after the restart, and restores and restarts once more if anything moved.
- If it can't save the snapshot, it stops before touching any files.

### Set it up

1. Save the script below as `/mnt/ssd-pool/apps/navidrome/update-navidrome-plugins.sh`. Keep it outside the `plugins` folder.
2. `sudo chmod +x /mnt/ssd-pool/apps/navidrome/update-navidrome-plugins.sh`
3. Dry run: `sudo CHECK_ONLY=1 /mnt/ssd-pool/apps/navidrome/update-navidrome-plugins.sh` shows each plugin as up to date, NEW or ADD, and changes nothing.
4. In TrueNAS go to **System → Advanced Settings → Cron Jobs → Add**:
   - Command: `/mnt/ssd-pool/apps/navidrome/update-navidrome-plugins.sh >> /mnt/ssd-pool/apps/navidrome/plugin-updates.log 2>&1`
   - Run As User: `root`
   - Schedule: Sundays at 05:00. That's after NaviBeat's 04:00 refresh, and AudioMuse has nothing scheduled at that time.
5. Run it by hand any time with `sudo /mnt/ssd-pool/apps/navidrome/update-navidrome-plugins.sh`.

**Rollback:** the previous version of each plugin is kept in `/mnt/ssd-pool/apps/navidrome/plugin-backups/`. To roll one back, copy it into `plugins/`, then run `plugin rescan`, `plugin enable <id>` and restart, same as the script.

**Adding a plugin later:** add a line to `PLUGINS=(...)` in the form `id|owner/repo|asset.ndp`.

**Keep AudioMuse aligned:** the AudioMuse docs say mismatched versions of the core app, the plugin and Navidrome are the most common source of errors. The script always fetches the latest plugin, so update the AudioMuse containers around the same time.

### update-navidrome-plugins.sh

```bash
#!/usr/bin/env bash
# update-navidrome-plugins.sh
#
# Installs or updates Navidrome plugins from their GitHub "latest" releases.
#
#   ./update-navidrome-plugins.sh                install new plugins, update changed ones
#   CHECK_ONLY=1 ./update-navidrome-plugins.sh   report what would change, touch nothing
#
# Why the extra steps after copying a file: Navidrome fingerprints every .ndp
# (SHA-256). When a file changes it marks the plugin disabled, because a new
# version may ask for new permissions. Your plugin settings are kept. This
# script re-enables only the plugins it just updated, then restarts Navidrome
# so the running server picks them up.
#
# Brand-new plugins are installed but NOT enabled: some need a one-time choice
# in Settings > Plugins first (which users / which libraries).
#
# Settings safety net: before changing anything it saves every plugin's settings,
# users and libraries to BACKUP_DIR/plugin-settings-<time>.json (last 10 kept).
# After an update it compares, and puts back anything that came back different,
# both before and after the restart.

set -euo pipefail

# --- settings ----------------------------------------------------------------
PLUGINS_DIR="/mnt/ssd-pool/apps/navidrome/plugins"
BACKUP_DIR="/mnt/ssd-pool/apps/navidrome/plugin-backups"   # last version of each, for rollback
CONTAINER="navidrome"
OWNER="3000:3000"
CHECK_ONLY="${CHECK_ONLY:-0}"

# plugin id (= file name without .ndp) | GitHub repo | release asset name
PLUGINS=(
  "audiomuseai|NeptuneHub/AudioMuse-AI-NV-plugin|audiomuseai.ndp"
  "nd-lyrics|J0R6IT0/navidrome-lyrics-plugin|nd-lyrics.ndp"
  "apple-music|navidrome/apple-music-plugin|apple-music.ndp"
  "navibeat-mixes|nenadjokic/navibeat-mixes|navibeat-mixes.ndp"
  "listenbrainz-daily-playlist|kgarner7/navidrome-listenbrainz-daily-playlist|listenbrainz-daily-playlist.ndp"
)
# -----------------------------------------------------------------------------

log() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }

# Prints the version from an .ndp's manifest.json (an .ndp is a zip file).
ndp_version() {
  python3 - "$1" <<'PY' 2>/dev/null || echo "?"
import json, sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
    print(json.loads(z.read("manifest.json")).get("version", "?"))
PY
}

# True if the file is a zip that contains manifest.json (catches HTML error pages, truncated downloads).
is_valid_ndp() {
  python3 - "$1" <<'PY' >/dev/null 2>&1
import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
    z.getinfo("manifest.json")
PY
}

nd() { docker exec "$CONTAINER" navidrome "$@"; }

# Saves every plugin's settings, users and libraries (Navidrome's own record) as JSON.
# Readable by root only: plugin settings can hold tokens (ListenBrainz, AudioMuse).
snapshot_state() { ( umask 077; nd plugin list -f json 2>/dev/null > "$1" ); }

# Compares one plugin's settings now against the snapshot and puts back anything that changed.
restore_settings() {
  local id="$1" before="$2" now="$STAGE/state-now.json" kind value
  snapshot_state "$now" || { log "WARN  could not read current settings for $id"; return; }
  while IFS=$'\t' read -r kind value; do
    RESTORED=1
    case "$kind" in
      CONFIG)  docker exec -i "$CONTAINER" navidrome plugin edit "$id" --config-file - < "$STAGE/$id.config.json" \
                 && log "      restored settings for $id" ;;
      USERS)   nd plugin edit "$id" --users "$value" && log "      restored users for $id" ;;
      ALLUSERS) nd plugin edit "$id" --all-users && log "      restored all-users access for $id" ;;
      LIBS)    nd plugin edit "$id" --libraries "$value" && log "      restored libraries for $id" ;;
      ALLLIBS) nd plugin edit "$id" --all-libraries && log "      restored all-libraries access for $id" ;;
    esac
  done < <(python3 - "$before" "$now" "$id" "$STAGE/$id.config.json" <<'PY'
import json, sys
before_path, now_path, pid, cfg_out = sys.argv[1:5]
load = lambda p: {x["id"]: x for x in json.load(open(p))}
b, n = load(before_path).get(pid), load(now_path).get(pid, {})
if not b:
    sys.exit(0)
if b.get("config") and b.get("config") != n.get("config"):
    open(cfg_out, "w").write(b["config"])
    print("CONFIG\t-")
if b.get("allUsers") and not n.get("allUsers"):
    print("ALLUSERS\t-")
elif b.get("users") and b.get("users") != n.get("users"):
    print("USERS\t" + b["users"])
if b.get("allLibraries") and not n.get("allLibraries"):
    print("ALLLIBS\t-")
elif b.get("libraries") and b.get("libraries") != n.get("libraries"):
    print("LIBS\t" + b["libraries"])
PY
)
}

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$PLUGINS_DIR" "$BACKUP_DIR"

# Snapshot every plugin's settings before touching anything. Kept in BACKUP_DIR,
# so a lost configuration can always be put back by hand with `navidrome plugin edit`.
STATE_BEFORE="$BACKUP_DIR/plugin-settings-$(date '+%Y%m%d-%H%M%S').json"
if [[ "$CHECK_ONLY" != "1" ]]; then
  if snapshot_state "$STATE_BEFORE" && [[ -s "$STATE_BEFORE" ]]; then
    ls -1t "$BACKUP_DIR"/plugin-settings-*.json 2>/dev/null | tail -n +11 | xargs -r rm -f   # keep the last 10
  else
    log "STOP  could not save current plugin settings (is the $CONTAINER container running?). Nothing changed."
    rm -f "$STATE_BEFORE"; exit 1
  fi
fi

updated=()
added=()
failed=()

for entry in "${PLUGINS[@]}"; do
  IFS='|' read -r id repo asset <<<"$entry"
  url="https://github.com/${repo}/releases/latest/download/${asset}"
  new="$STAGE/${id}.ndp"
  dest="$PLUGINS_DIR/${id}.ndp"

  if ! curl -fsSL --retry 3 --connect-timeout 15 -o "$new" "$url"; then
    log "FAIL  $id: download failed ($url)"; failed+=("$id"); continue
  fi
  if ! is_valid_ndp "$new"; then
    log "FAIL  $id: downloaded file is not a valid .ndp, leaving current version alone"; failed+=("$id"); continue
  fi

  new_ver="$(ndp_version "$new")"
  if [[ -f "$dest" ]] && cmp -s "$new" "$dest"; then
    log "OK    $id $new_ver (up to date)"; continue
  fi

  if [[ -f "$dest" ]]; then
    old_ver="$(ndp_version "$dest")"
    log "NEW   $id $old_ver -> $new_ver"
    [[ "$CHECK_ONLY" == "1" ]] && continue
    cp -p "$dest" "$BACKUP_DIR/${id}.ndp"
    updated+=("$id")
  else
    log "ADD   $id $new_ver (not installed yet)"
    [[ "$CHECK_ONLY" == "1" ]] && continue
    added+=("$id")
  fi

  # Write next to the target, then rename, so Navidrome never sees a half-written file.
  install -m 0644 -o "${OWNER%%:*}" -g "${OWNER##*:}" "$new" "$dest.part"
  mv -f "$dest.part" "$dest"
done

if [[ "$CHECK_ONLY" == "1" ]]; then
  log "Check only, nothing changed."
  exit 0
fi

if (( ${#updated[@]} + ${#added[@]} > 0 )); then
  log "Syncing Navidrome's plugin list"
  nd plugin rescan

  for id in "${updated[@]}"; do
    restore_settings "$id" "$STATE_BEFORE"
    if nd plugin enable "$id"; then
      log "      re-enabled $id"
    else
      log "WARN  could not re-enable $id. Enable it in Settings > Plugins (check its users/libraries)."
    fi
  done

  log "Restarting $CONTAINER"
  docker restart "$CONTAINER" >/dev/null

  # Check again once Navidrome is back up, in case startup itself changed anything.
  sleep 20
  RESTORED=0
  for id in "${updated[@]}"; do restore_settings "$id" "$STATE_BEFORE"; done
  if (( RESTORED )); then
    log "Settings changed during restart and were put back. Restarting $CONTAINER again."
    for id in "${updated[@]}"; do nd plugin enable "$id" >/dev/null 2>&1 || true; done
    docker restart "$CONTAINER" >/dev/null
  else
    log "      settings verified after restart"
  fi
fi

(( ${#added[@]} > 0 )) && log "Installed but not enabled yet: ${added[*]}  -> Settings > Plugins"
(( ${#failed[@]} > 0 )) && { log "Failed: ${failed[*]}"; exit 1; }
log "Done."
```

## Considered and skipped

Most of the rest either duplicate one of the five above or need hardware or apps you don't run. The ones worth revisiting are marked.

| Repo | What it does | Why not now |
| --- | --- | --- |
| [daviidpaark/tuneshine-navidrome](https://github.com/daviidpaark/tuneshine-navidrome) | Sends now-playing album art to a [Tuneshine](https://www.tuneshine.rocks/) 64×64 LED display | **Fun pick if you buy the display** ($200 in beech, $220 in walnut). The display already supports Last.fm, Plex and Apple Music on its own, so it shows everything you scrobble. The plugin only makes Navidrome plays show up instantly. Active (v0.4.6, updated Sep 30). |
| [mythezone/navidrome-music-room](https://github.com/mythezone/navidrome-music-room) | Synced listening rooms: everyone signs in with their own Navidrome account and hears the same queue | **Revisit later.** It's a neat fit for a family library, but it's a v1.1.0-dev prerelease built over three days in September. |
| [sunsetroute1/navidrome-coverartarchive-plugin](https://github.com/sunsetroute1/navidrome-coverartarchive-plugin) | Album art from MusicBrainz / Cover Art Archive | **Revisit if covers go missing.** It only runs when an album has no local art, and Picard and Tidarr embed it. |
| [xmorose/spindle](https://github.com/xmorose/spindle) | Self-hosted listening stats dashboard (plugin plus its own container) | **Revisit if you want a private Last.fm.** It's a whole extra app, and Last.fm and ListenBrainz already have your history. |
| [madmax1301/tonus-navidrome-plugin](https://github.com/madmax1301/tonus-navidrome-plugin) | Mirrors ListenBrainz playlists and downloads the missing tracks through its own tonus backend | It downloads outside Lidarr, which brings back the duplicate-source problem. Aurral already covers finding new music. |
| [TheRaphael0000/clapclap\_navidrome](https://github.com/TheRaphael0000/clapclap_navidrome) | A second sonic-similarity backend for Instant Mix | Competes with AudioMuse for the same agent slot. Only one can answer Instant Mix. |
| [egecelikci/navidrome-listenbrainz-plugin](https://github.com/egecelikci/navidrome-listenbrainz-plugin) | Two-way sync of Navidrome favorites and ListenBrainz loves | Its own README says it was fully written by an LLM and nobody has reviewed or tested it. It's two days of commits old. |
| [scatolo/dztnr](https://github.com/scatolo/dztnr) | Overwrites star ratings with Deezer popularity | It's crowd popularity, not your taste, and you use favorites rather than stars. NaviBeat's Loved and Rediscover mixes already work from your favorites. |
| [Myzel394/navidrome-musixmatch-plugin](https://github.com/Myzel394/navidrome-musixmatch-plugin) | Musixmatch lyrics | Covered by lrcmux in nd-lyrics. Its analytics are on unless you opt out, and the author says the scraping breaks often. |
| [craiglush/navidrome-mood-plugin](https://github.com/craiglush/navidrome-mood-plugin) | Mood playlists from its own audio analyzer | AudioMuse already does this. No commits since March. |
| [craiglush/navidrome-vibe](https://github.com/craiglush/navidrome-vibe), [pirus99/magic-lists-ai-curator](https://github.com/pirus99/magic-lists-ai-curator), [baba537/Cantilune](https://github.com/baba537/Cantilune) | Text-prompt and situation playlists | Overlap with AudioMuse's CLAP text search and NaviBeat. |
| [bcorporaal/navidrome-play-it-again](https://github.com/bcorporaal/navidrome-play-it-again) | Surfaces neglected music | Same idea as NaviBeat Rediscover and Weekly Discovery. |
| [andykelk/navidrome-ntfy-plugin](https://github.com/andykelk/navidrome-ntfy-plugin) | ntfy/webhook alert when an album is added | Only worth it if you want push alerts outside Lidarr's own notifications. |
| [e1025735/nd-rating-sync](https://github.com/e1025735/nd-rating-sync) | Imports star ratings from MusicBee, foobar2000 and MediaMonkey tags | Beta, and only useful if your files carry ratings written by those players. |
| [navidrome/discord-rich-presence-plugin](https://github.com/navidrome/discord-rich-presence-plugin) | Now-playing in Discord status | Needs your Discord user token, which its own README warns may break Discord's terms. |
| [metalheim/...artist-nfo-metadata](https://github.com/metalheim/navidrome-plugin-artist-nfo-metadata) | Artist bios and photos from Kodi-style `artist.nfo` files | You don't have `.nfo` files, and Apple Music already covers artist pages. |
| [Tal0na/plugin-watcher-0navidrome](https://github.com/Tal0na/plugin-watcher-0navidrome) | Notifies when plugin updates exist | Notify-only, 3 commits. The script above updates them instead. |
| Lyrics extras: [shazam](https://github.com/Myzel394/navidrome-shazam-plugin), [lyricstranslate](https://github.com/Myzel394/navidrome-lyricstranslate-plugin), [lrclib](https://github.com/kepelet/navidrome-lrclib-plugin), [better-lyrics](https://github.com/ranokay/navidrome-better-lyrics-plugin), [apm-lyrics](https://github.com/noaione/apm-lyrics-ndp) | Single-source lyrics | nd-lyrics covers these sources in one plugin. |
| NetEase and Qobuz metadata (sky8282, ikelvingo, XBisATrouble, yuehei) | Chinese-catalog and Qobuz metadata | Apple Music covers your catalog. |

Sources: [GitHub navidrome-plugin topic](https://github.com/topics/navidrome-plugin), each repo's README and manifest (cloned Oct 7), [Navidrome plugin docs](https://www.navidrome.org/docs/usage/features/plugins/), and Navidrome source `plugins/manager_sync.go` and `cmd/plugin.go`.
