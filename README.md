# homelab-music-toolkit

A self-hosted web app for a Navidrome + AudioMuse-AI homelab music setup. It replaces a pile of cron-scheduled Python scripts *and* a separate duplicate-music-finder container with one app: one Docker image, one `/config` volume, one UI.

**What it does, in rough priority order:**

1. **Duplicate finder** — finds duplicate tracks, explains why with raw tags and audio checksums, quarantines the extras (reversible) or deletes them for good (explicit, confirmed).
2. **Cluster cleanup** — takes stray worship songs out of AudioMuse's `_automatic` clustering playlists when they're a minority of the playlist.
3. **Tidarr import filing** — tags and prefixes playlists Navidrome imported from Tidarr so they group together in every client.
4. **Playlist folders** — files playlists into `Folder/Subfolder/Name` folders by renaming them, from an editable map.
5. **Fix m3u paths** — repoints broken `.m3u` entries at the files you actually have, with a backup of every playlist it touches.
6. **Playlist cover art** — generates real cover art for playlists (AI photography via Replicate, or curated background + typography), applied the way Navidrome actually supports: a sidecar image or its playlist-image upload API.
7. **Prompts library** — the Apple Music playlist prompts and recipes, searchable, with a "Run in AudioMuse" button that creates the playlist for you.
8. **Playlist Studio** — an iterative workshop on top of AudioMuse: blend several of your own library's tracks into one playlist (Alchemy), or generate from a free-text prompt, then refine in plain language and see a diff before committing.
9. **Scheduler** — built-in scheduled jobs (replacing the old TrueNAS cron jobs) with enable/disable, a schedule editor and full run history.
10. **Status page** — Navidrome and AudioMuse reachability, versions, playlist counts, last run of every job.

Every write operation previews by default; applying is a separate, explicit action.

> **This app holds your Navidrome admin password and can permanently delete files from your music library.** A login is **required by default** — see [Configuration](#configuration) below. Don't disable it unless something else in front of this app (a reverse proxy with its own auth) is doing that job instead.

---

## Contents

- [Install](#install)
  - [TrueNAS SCALE](#truenas-scale)
  - [Docker Compose (generic)](#docker-compose-generic)
  - [Build the image yourself](#build-the-image-yourself)
- [Configuration](#configuration)
- [First-run setup](#first-run-setup)
- [Migrating from the manual scripts and cron jobs](#migrating-from-the-manual-scripts-and-cron-jobs)
- [Migrating from the standalone docker-music-dupes container](#migrating-from-the-standalone-docker-music-dupes-container)
- [Using it](#using-it)
  - [Duplicate finder](#duplicate-finder)
  - [Cluster cleanup](#cluster-cleanup)
  - [Tidarr import filing](#tidarr-import-filing)
  - [Playlist folders](#playlist-folders)
  - [Fix m3u paths](#fix-m3u-paths)
  - [Playlist cover art](#playlist-cover-art)
  - [Prompts library](#prompts-library)
  - [Playlist Studio](#playlist-studio)
  - [Scheduler](#scheduler)
- [How the duplicate finder decides](#how-the-duplicate-finder-decides)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [What's deliberately not built yet](#whats-deliberately-not-built-yet)
- [License](#license)

---

## Install

The image is published to GitHub Container Registry for `linux/amd64` and `linux/arm64`:

```
ghcr.io/mikestecker/docker-homelab-music-toolkit:latest
```

Two mounts matter everywhere you install it:

| Container path | What to mount | Mode |
|---|---|---|
| `/music` | Your music library, as **one** mount | read-write |
| `/config` | App state (a few MB — quarantine manifest, tag cache, worship artist list, playlist folder map, job schedules, run history) | read-write |

The library must be a single mount. The duplicate finder's quarantine is a rename within `/music/.dupe-quarantine/`, which is instant inside one filesystem — splitting the library across mounts turns that into a slow cross-device copy. The other Navidrome/AudioMuse modules only ever talk to Navidrome's API, not the filesystem, except the m3u fixer, which also needs `/music` read-write for the same reason.

### TrueNAS SCALE

TrueNAS Custom Apps don't read `.env` files (every `${VAR}` resolves to an empty string), so [`deploy/truenas.yaml`](deploy/truenas.yaml) inlines everything.

1. Create a dataset or folder for state, owned by whichever user/group your music library is owned by (check with `ls -ln` on your music dataset — don't assume `3000:3000`; that's just TrueNAS SCALE's common `svc_apps` default, not a given):

   ```bash
   sudo mkdir -p /mnt/<your-pool>/apps/homelab-music-toolkit/config
   sudo chown -R <uid>:<gid> /mnt/<your-pool>/apps/homelab-music-toolkit
   ```

2. Open `deploy/truenas.yaml` and replace every `REPLACE_WITH_...` / `paste_..._here` placeholder: your UID:GID, timezone, pool path, Navidrome/AudioMuse host and credentials, and the Lidarr values if you use it (or delete those lines).
3. **Apps → Discover Apps → ⋮ → Install via YAML**, name it `homelab-music-toolkit`, paste the file.
4. Open `http://<nas-ip>:8095` and log in with the `AUTH_USER`/`AUTH_PASS` you set.

Separate TrueNAS apps can't reach each other by container name, so `ND_URL`, `AUDIOMUSE_URL` and `LIDARR_URL` all use the NAS IP, not a container name.

### Docker Compose (generic)

```bash
git clone https://github.com/mikestecker/docker-homelab-music-toolkit.git
cd docker-homelab-music-toolkit
cp .env.example .env
# edit .env: MUSIC_PATH, AUTH_USER/AUTH_PASS, ND_URL/ND_USER/ND_PASS, AUDIOMUSE_URL/AUDIOMUSE_API_TOKEN
docker compose up -d --build       # build locally, or:
docker compose -f deploy/compose.no-build.yaml up -d   # pull the published image
```

Find the right `PUID`/`PGID` with `ls -ln` on your music folder, or `id -u`/`id -g` for the user that owns it.

### Build the image yourself

```bash
docker build -t homelab-music-toolkit .
```

Then set `IMAGE=homelab-music-toolkit` in `.env`, or use that name directly with `docker run`.

---

## Configuration

Everything is environment variables, set at the container level — never in files inside the repo.

| Variable | Default | What it does |
|---|---|---|
| `AUTH_USER` / `AUTH_PASS` | — | The login for the whole app (its own login page, not your Navidrome one). **Required unless `AUTH_DISABLED=1`** — the app refuses to start otherwise. |
| `AUTH_DISABLED` | unset | Set to `1` only if something else (a reverse proxy with its own auth) is already gating access. |
| `ALLOWED_HOSTS` | — | Extra hostnames the UI answers to, comma-separated, e.g. `toolkit.example.com`. IPs, single-word names and `.local`/`.lan`/`.home.arpa`/`.internal` names always work without this. `*` turns the check off. Protects against DNS-rebinding attacks from other websites. |
| `ND_URL` | — | Navidrome base URL, e.g. `http://<your-navidrome-host>:4533` |
| `ND_USER` / `ND_PASS` | — | The Navidrome user AudioMuse logs in as. Cluster cleanup, Tidarr tagging and playlist folders all act as this user, and can only edit playlists it owns (or that it's an admin over). |
| `AUDIOMUSE_URL` | — | AudioMuse-AI base URL, e.g. `http://<your-audiomuse-host>:8000` |
| `AUDIOMUSE_API_TOKEN` | — | From AudioMuse's Setup Wizard. Used for the prompts library's "Run in AudioMuse" and playlist-creation calls. |
| `REPLICATE_API_TOKEN` | — | From [replicate.com/account/api-tokens](https://replicate.com/account/api-tokens). Only needed for AI-mode cover art — template mode (curated backgrounds + typography) needs neither this nor network access. Leave unset and AI mode just disables itself in the UI. |
| `REPLICATE_MODEL` | `google/imagen-4` | An `owner/name` *official-model* id on Replicate — official models always run their latest version, so there's no version hash to track. `google/imagen-4` is photorealistic (~$0.04/image); `google/imagen-4-fast` is the same model family at roughly half the price (~$0.02/image) and is "good enough" for most playlist covers; `black-forest-labs/flux-dev` (~$0.025/image) is a non-Google alternative. Check [replicate.com/pricing](https://replicate.com/pricing) for current numbers — Replicate changes these from time to time. |
| `PREFER_SOURCES` | `Tidarr` | Duplicate finder: when copies are otherwise equal, keep the one whose Source label contains the first of these (comma-separated). Empty turns it off. |
| `PREFER_REMASTERS` | `true` | Duplicate finder: prefer a remastered edition as a tiebreak. `false` prefers originals. |
| `FINGERPRINT` | `report` | Duplicate finder: `report` shows what acoustic fingerprints would change without acting on it, `on` lets them confirm/veto duplicates, `off` skips them. |
| `FINGERPRINT_WORKERS` | CPUs the container may use | Parallel `fpcalc` processes. |
| `LIDARR_URL` / `LIDARR_API_KEY` / `LIDARR_MUSIC_ROOT` | — / — / `/data/media/music` | Optional: labels duplicate-finder files with the download client Lidarr imported them from. |
| `PORT` | `8095` | Port the app listens on inside the container. |
| `MUSIC_DIR` / `CONFIG_DIR` | `/music` / `/config` | Container-internal paths — change these only if you also change the volume mounts to match. |
| `TZ` | `UTC` | Timezone for timestamps, quarantine batch names and the scheduler's clock. |

### Files under `/config`

| File | What it is |
|---|---|
| `tags.db` | Duplicate finder's SQLite tag + fingerprint cache. Safe to delete; the next scan rebuilds it. |
| `quarantine.json` | What's in each quarantine batch, so restores know where files go back to. **Never delete this by hand** while anything is quarantined. |
| `kept-both.json` | Albums you marked "Keep both" in the duplicate finder. |
| `sources.json` | Your own source-detection rules for the duplicate finder. |
| `worship-artists.txt` | Cluster cleanup's artist list, seeded from a sensible default on first boot. |
| `cleanup-settings.json` | Cluster cleanup's `max_share`/`min_seconds`/`rename_prefix`. |
| `tidarr-tagging-settings.json` | Tidarr filing's prefix/path-match settings. |
| `playlist-folders.txt` | The playlist-folder map, seeded from a default on first boot. This is the source of truth — UI edits write back to it. |
| `m3u-fix-settings.json` | The m3u fixer's playlist-folder and host-root settings. |
| `cover-backgrounds/` | Your own uploaded backgrounds for template-mode cover art, alongside the 150 built-in ones. |
| `covers/<playlist-id>/` | Generation history for that playlist's cover art — every template or AI generation, so you can reuse or re-apply one without regenerating (or spending another Replicate call). |
| `job-schedules.json` / `run-history.json` | The scheduler's state. |
| `session-secret.txt` | Generated on first login, signs the login session cookie. Deleting it logs everyone out (not destructive — just log back in with `AUTH_USER`/`AUTH_PASS`). |
| `playlist-studio/<session-id>/` | Playlist Studio's per-session generation history (Instant/Alchemy/refine attempts and their track lists). |

---

## First-run setup

1. **Log in.** Opening the app shows its own login page — enter the `AUTH_USER`/`AUTH_PASS` you set. The session lasts about three weeks and renews itself while you're using the app, so this isn't a daily thing; **Log out** is at the bottom of the sidebar. `curl -u user:pass` still works against the API directly, for scripting.
2. **Get your AudioMuse API token.** Log into AudioMuse's web UI once, then its Setup Wizard gives you a token for machine-to-machine calls. Put it in `AUDIOMUSE_API_TOKEN`.
3. **Confirm the Navidrome user.** `ND_USER` needs to be the exact user AudioMuse logs in as — only that user (or an admin) can edit the `_automatic` cluster playlists AudioMuse creates.
4. **Check the seeded defaults.** On first boot, `worship-artists.txt` and `playlist-folders.txt` are copied from sensible starting points into `/config`. Edit them from the Cluster cleanup and Playlist folders pages (or by hand on the host — they're plain text).
5. **Preview before you apply, everywhere.** Every module defaults to a dry run. Look at a preview's result before hitting Apply, especially the first time.
6. **Leave schedules off until you trust the preview.** Cluster cleanup and Tidarr filing come enabled by default (matching the old cron jobs), at 03:00 and 06:15. Turn them off from the Scheduler page first if you want to watch a few manual runs before trusting the automation.

---

## Migrating from the manual scripts and cron jobs

| Old TrueNAS cron job | Old location | New home |
|---|---|---|
| `clean-clusters.py`, daily | `/mnt/ssd-pool/apps/audiomuse/cluster-cleanup/` | Scheduler → **Cluster cleanup** (enabled by default, 03:00) |
| `tag-tidarr-playlists.py --apply`, daily 06:15 | `/mnt/ssd-pool/apps/navidrome/scripts/` | Scheduler → **Tidarr import filing** (enabled by default, 06:15) |

Steps:

1. Deploy this app and let it run **manually** (Preview, then Apply) on both Cluster cleanup and Tidarr filing a few times, so you trust the output against your real library.
2. Open the Scheduler page and confirm both jobs are enabled with the schedule you want.
3. Watch the run history for a day or two — each scheduled run's full output is there, same as the old cron job's log would have shown.
4. Once you're confident, remove the two TrueNAS cron jobs (**System Settings → Advanced → Cron Jobs**) that ran `clean-clusters.py` and `tag-tidarr-playlists.py`.
5. The old script folders on the NAS (`/mnt/ssd-pool/apps/audiomuse/cluster-cleanup/`, `/mnt/ssd-pool/apps/navidrome/scripts/`) are no longer read by anything. Archiving them (rename to `*.bak` or move under a `_retired/` folder) is safer than deleting outright, in case you want to diff against the old `cleanup.env`/`navidrome.env`/`playlist-folders.txt` values while you set up the new app's `/config` versions.
6. `rename-playlists.py` and `fix-m3u-paths.py` weren't cron jobs before (you ran them by hand) — their new homes are the **Playlist folders** and **Fix m3u paths** pages, same behavior, no schedule needed unless you choose to add one.
7. **`update-navidrome-plugins.sh` stays exactly where it is.** It's out of scope for this app on purpose — it needs `docker exec`/`docker restart` on Navidrome, and giving this app the Docker socket to do that would effectively hand it root on your NAS. Keep it as a host cron job.

The scripts' own CLI entry points still exist too (`python -m app.cli.cluster_cleanup --apply`, etc. — run with `docker exec` into the container), in case you ever want to run one outside the scheduler or the UI.

---

## Migrating from the standalone docker-music-dupes container

The duplicate finder here is docker-music-dupes, ported in place — same scan, same classification rules, same quarantine format. Moving your existing deployment over:

1. **Stop the old `music-dupes` container**, but don't delete its volumes yet.
2. **Point this app's `/config` and `/music` mounts at the same host paths** the old container used. The `quarantine.json` manifest and `tags.db` tag/fingerprint cache have the same shape, so this is a drop-in volume swap — you should **not** need to re-scan from scratch. (If a future release of this app ever does change the cache format, it bumps the table name the same way the original project always did, and the next scan just re-reads tags once; that'll be called out in the changelog if it happens.)
3. **Carry over your settings as environment variables on the new container**: `PREFER_SOURCES`, `PREFER_REMASTERS`, `FINGERPRINT`, `FINGERPRINT_WORKERS`, `LIDARR_URL`, `LIDARR_API_KEY`, `LIDARR_MUSIC_ROOT` are all unchanged env var names. Add the new ones this app needs on top (`AUTH_USER`/`AUTH_PASS`, `ND_URL`/`ND_USER`/`ND_PASS`, `AUDIOMUSE_URL`/`AUDIOMUSE_API_TOKEN`).
4. **Start this app and open the Duplicate finder page.** Your quarantine history and cached tags should already be there.
5. **Remove the old `docker-music-dupes` deployment** (compose stack or TrueNAS Custom App) once you've confirmed the new one is working.
6. **Archive the `docker-music-dupes` GitHub repo**, if you'd like — it's no longer the actively developed copy of this code. That's your call, not something done automatically.

---

## Using it

### Duplicate finder

Click **Scan library**. The first scan reads tags from every audio file, so on a big library over spinning disks, expect it to take a few minutes; results are cached by path/size/modification-time, so later scans only re-read files that changed.

**Sections:**

- **Suggested** — the app is confident. Redundant copies are already selected; look it over and hit **Quarantine selected**.
- **Review** (shown as `manual`) — the app can't decide (different artists, different recordings, can't confirm). Nothing is pre-selected.
- **Other albums** — the same recording on different releases (an album, a single, a best-of). Both stay; nothing is selected.
- **Kept both** — albums you've told it to leave alone, via the "Keep both" button. If a new copy shows up later, it comes back for review.

**Quarantine** is a reversible rename into a hidden folder inside the library — restore any batch, or **Delete permanently** as an explicit, confirmed, separate action.

### How the duplicate finder decides

The short version, in order of strength:

1. **Identical audio.** FLAC files store an MD5 of the decoded audio. Same MD5 means bit-identical audio, no matter how the tags or file names differ.
2. **Same ISRC** and lengths within 1.5 seconds means the same recording, even across formats.
3. **Same acoustic fingerprint** over the full length (with `FINGERPRINT=on`). For copies with no shared ISRC, like a Lidarr retag next to a Tidarr download.
4. **Same disc/track slot in one folder** with lengths within a second.

Then, per album pair:

- Different album artists → Review.
- Different albums (an album and a single, a compilation or a best-of that share a recording) → **Other albums**, nothing selected. Both releases stay whole. Album names are compared without edition wording (deluxe, remaster, special edition, a year), and close spellings like `Fractured Heart` / `Fractioned Heart` still count as one album.
- Any track with different ISRCs, or lengths more than 2.5s apart → Review.
- One copy tagged clean or edited (advisory tag, or "(Clean)" / "(Edited)" in the title) and another not → Review. They're different releases.
- With `FINGERPRINT=on`, any track whose fingerprints disagree → Review: different audio, a cut version, or short passages that differ (often a clean edit).
- One folder only holds tracks that are all in a more complete copy of the same album (say Tidarr grabbed three songs Lidarr already has) → suggest keeping the complete album. Every track must be within a second, and audio that's provably different is never covered.
- One edition is deluxe/expanded/special and the other isn't, and the deluxe one is at least as complete → suggest keeping the deluxe one.
- Every track proven identical or the same recording → suggest keeping the best quality, then the most tracks, then your preferred source, then tags Lidarr didn't rewrite, then a remastered edition (`PREFER_REMASTERS`), then the richest tags, then the earliest year. The card names the step that decided it. When the checksums show two different masters of the same recording, tracks get a "Different master" chip and the card asks you to listen first.
- Anything else → Review.

Last check: if the edition it would keep has a lower-quality copy of any track than the one it would remove (say a CD-quality deluxe vs a hi-res standard), the whole album gets bumped to Review. When that's a partial folder holding hi-res copies of a CD-quality album, the reason says so, and the better file gets an **Upgrade** button: it moves into the album under the album copy's name and the lower-quality copy goes to quarantine. Restore puts both back.

Titles that differ only by a featured artist (`Rest` vs `Rest (with Samm Henshaw)`, `feat.`, `ft.`) count as the same track, with a "Credits differ" note.

**Which copy stays.** Within a folder the keeper is ranked by, in order:

1. Quality class (hi-res, then CD-quality lossless, then lossy). 44.1 kHz and 48 kHz at the same bit depth count as equal.
2. Fit with the folder: named like the other tracks, written in the same download batch, and a filename that agrees with its own track tags.
3. A filename that matches its title tag.
4. An ISRC, when another copy has none (Lidarr retags often strip them).
5. Your `PREFER_SOURCES` (Tidarr by default).
6. Tags Lidarr didn't rewrite.
7. Then exact sample rate, no ` (1)` in the name, more tags, older file.

The kept copy says why, from the first step that separated it from the other. Newer isn't better on its own — a re-download can carry a mangled name. FLAC bitrate is never used as a quality signal (it's only used as an integrity check for truncated files).

**Safety guarantees (unchanged from docker-music-dupes, and never weakened):**

- Never removes every copy of a track — checked in the browser **and** on the server.
- Nothing is deleted without an explicit, confirmed **Delete permanently** on a quarantine batch.
- Only files under the library mount (and outside the quarantine folder, and never through a symlink) can be read, played or moved.
- Restore never overwrites a file that's come back in the meantime.
- Quarantine re-checks the disk first: if the kept copy is gone or changed, or the file being moved isn't the one that was scanned, that track is skipped until the next scan.
- FLAC copies with the same audio checksum but much less audio data (a cut-short download) go to Review instead of counting as identical.
- `quarantine.json` is never silently reset when it's unreadable — quarantine, restore and purge refuse to run instead, so a corrupt manifest can't orphan a batch.

### Cluster cleanup

Edit the worship artist list and the `max_share`/`min_seconds`/`rename_prefix` settings, then **Preview** before **Apply**. Removal only happens when listed artists are a *minority* of a clustering playlist (`max_share`, default 34%) — a cluster that's mostly worship is left alone. Songs shorter than `min_seconds` (intros, interludes) are dropped too, when set.

### Tidarr import filing

Prefixes (default `Imports/Tidarr/`) and comments every playlist Navidrome imported from Tidarr's `.m3u` folder, so they group together in every client. **Undo** removes the prefix and comment again. Safe to run daily — a playlist that's already tagged is skipped.

### Playlist folders

Shows every current playlist grouped by its implied folder. **Assign** writes an exact-match rule into the map file; edit the map directly for prefix rules (`prefix: OldPrefix => NewPrefix/`) or bulk changes. Preview, then Apply to actually rename in Navidrome. Two folder levels deep is the convention Feishin's folder view expects.

### Fix m3u paths

Finds `.m3u` entries that no longer resolve (a re-download changed the extension, folder or edition) and matches them to what's actually in your library now, by artist folder and track title. Every applied fix keeps a timestamped backup of the original playlist file, listed (and deletable) from this page.

### Playlist cover art

Pick a playlist, pick a layout (6 options — bottom banner, top editorial, big bleed, center badge, sidebar, vinyl badge) and a font (7 bundled, OFL-licensed), then generate a cover in one of two modes:

- **Template** — pick from 150 built-in backgrounds (procedurally generated gradients/mesh/contour art, plus curated real photography) or one you've uploaded, and the playlist name is composited on top as a real font layer.
- **AI** — a photorealistic background generated by Replicate (needs `REPLICATE_API_TOKEN`/`REPLICATE_MODEL`; the AI button disables itself if those aren't set), from a style preset (10 options) optionally informed by the playlist's own track names. The title is always added afterward as the same font layer as template mode — the AI model is explicitly instructed never to render text itself, since image models reliably garble lettering, and a separate text layer means renaming a playlist never costs another generation.

Every generation is kept in a per-playlist history so you can flip back to an earlier one or re-apply it without regenerating. **Apply** writes the cover the way Navidrome actually supports it:

- For playlists backed by a `.m3u`/`.m3u8`/`.nsp` file (Tidarr imports, smart playlists), it writes a same-named image file next to it — Navidrome's sidecar convention, picked up automatically, no restart needed.
- For playlists with no backing file (created directly in Navidrome's UI), it calls Navidrome's playlist-image upload API instead. **This needs `ND_USER` to be a Navidrome admin, or `EnableArtworkUpload` set in Navidrome's own config** — that's a Navidrome-side prerequisite, not something this app can grant itself. If neither is true, Apply fails with a 502 explaining exactly that; the sidecar path (the common case for this library) has no such requirement.

**Remove** deletes the sidecar file or calls the matching delete endpoint, and Navidrome falls back to its own auto-generated track-tile artwork.

### Prompts library

Search and filter the Apple Music playlist prompts and recipes. **Copy** puts the prompt text on your clipboard. **Run in AudioMuse** sends it to AudioMuse's Instant Playlist API, shows the songs it returns, and lets you name the playlist (defaulting to `Occasions/<name>`, matching the folder convention above) before creating it on Navidrome. **Refine in Studio** hands a library prompt over to Playlist Studio below as a starting point, instead of a one-shot run.

### Playlist Studio

An iterative workshop for building a playlist, rather than one-shot "Run in AudioMuse": generate, describe a tweak in plain language, see what actually changed, decide whether to keep it, repeat.

- **Instant** — the same free-text-to-AudioMuse flow as the prompts library, but with the refine loop below.
- **Alchemy** — search your own library (via AudioMuse's own track index, not Navidrome's) and pick a few tracks as **Include** anchors (optionally some **Exclude** ones too), set a size and a variety preference, and it blends them into one playlist via AudioMuse's real `POST /api/alchemy`. That request shape is fully documented in AudioMuse's own API spec; its *response* shape isn't (just "each row contains the song and its centroid," no schema), so the parser tries a couple of plausible shapes inferred from sibling endpoints that are documented, rather than one guessed blind — if it's ever wrong, the raw response is kept so it can be fixed from a real example.
- **Refine** — type a change ("more upbeat", "less rap", "swap in some 90s") and it re-generates and shows a diff: new tracks, removed tracks, and which ones moved — before you commit to it.
- Every attempt in a session is kept, so you can jump back to an earlier result without regenerating or spending another request.

### Scheduler

Enable/disable each job, set its daily time, trigger a run immediately, and drill into any past run's full output — scheduled or manual. A scheduled run always applies for real; there's no such thing as a scheduled preview, since that would just silently do nothing.

---

## Troubleshooting

**The container won't start, complaining about AUTH_USER/AUTH_PASS.** Set both, or set `AUTH_DISABLED=1` if you really want to run without auth (not recommended — see the warning at the top of this README).

**Permission denied when quarantining or writing playlists, or the container won't start.** The container user can't write to your library or config folder. Check ownership with `ls -ln` and set `PUID`/`PGID` (or `user:`) to match.

**Quarantine is slow, or you see cross-device errors.** The music folder is split across several mounts. Mount the whole library once at `/music`.

**"This app doesn't answer to the hostname ..."** You're reaching it by a domain name it doesn't know. Add it to `ALLOWED_HOSTS`.

**Lidarr sources show "Not from Lidarr" for everything.** `LIDARR_MUSIC_ROOT` doesn't match the path Lidarr uses — check a file's path in Lidarr's history.

**A Navidrome full-library scan started and the UI "crashed."** It didn't — a full scan of a large library takes Navidrome itself roughly 15–20 minutes and looks unresponsive the whole time. This app never triggers one; if you see this, something else (Navidrome's own folder watcher catching up after a big import) is the cause. Give it time.

**A playlist rename didn't stick after Navidrome re-imports its `.m3u`/`.nsp` file.** It should — Navidrome keeps a playlist's renamed name across re-imports from the same file. If it didn't, check you're not accidentally running the old script and this app against the same playlist at the same time.

**The AI button on the cover art page is disabled.** `REPLICATE_API_TOKEN` and/or `REPLICATE_MODEL` aren't set. Template mode (curated backgrounds + typography) works regardless — it needs neither.

**Cover art generation fails with a 502 mentioning Replicate.** Usually an expired or invalid token — Replicate's free "getting started" tokens are short-lived demo tokens, not permanent ones; generate a real token at [replicate.com/account/api-tokens](https://replicate.com/account/api-tokens) if you hit this.

**Applying a cover art fails with "Navidrome refused the cover upload (403)".** That playlist has no backing file, so this app used Navidrome's upload API instead of writing a sidecar image — and Navidrome itself rejected it. `ND_USER` needs to be a Navidrome admin, or `EnableArtworkUpload` needs to be set in Navidrome's own config. This app can't grant either of those; it's a Navidrome-side setting.

**Logged out unexpectedly.** Either the session genuinely expired (about three weeks of inactivity), or `/config/session-secret.txt` got reset (a fresh config volume, or the file was deleted) — either way, just log back in.

**Can't log in at all.** Same check as before: `AUTH_USER`/`AUTH_PASS` are set correctly and match what you're typing. The login page itself doesn't trigger a browser popup — if you're seeing one, you're on an old build; rebuild and redeploy.

**Check it's alive:** `curl http://localhost:8095/healthz` should return `{"ok":true}`. The image also has a Docker healthcheck, so `docker ps` shows `(healthy)`.

---

## Development

```
app/
  main.py                 FastAPI app factory: routers, auth, host-allowlist middleware
  core/                   shared config, auth, Navidrome/AudioMuse clients, scheduler
  modules/
    duplicate_finder/     ported from docker-music-dupes, verbatim logic
    cluster_cleanup/      ported from clean-clusters.py
    tidarr_tagging/       ported from tag-tidarr-playlists.py
    playlist_folders/     ported from rename-playlists.py
    m3u_fix/              ported from fix-m3u-paths.py
    playlist_covers/      net-new: AI (Replicate) + template cover art, sidecar/upload apply
    playlist_studio/      net-new: Alchemy + refine/diff workshop on top of AudioMuse
    prompts_library/      Apple Music prompts/recipes data + AudioMuse calls
    scheduler/, status/   net-new: job scheduling, run history, status page
  cli/                    thin CLI wrappers, so each module still runs via `docker exec`
frontend/                 React + TypeScript (Vite)
tests/                    pytest suite, incl. fake-Navidrome/AudioMuse servers
docs/playbook/            the original AudioMuse Playbook, carried over as reference
config-defaults/          seed files copied into /config on first boot
```

Backend tests (need `ffmpeg` on your PATH for the duplicate-finder fixture library; fingerprint-specific tests also need `fpcalc` from `libchromaprint-tools`, and are skipped without it):

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

Nothing in the test suite ever runs against a real Navidrome or AudioMuse server — the Navidrome-script modules are tested against small fake HTTP servers in `tests/mocks/`.

Frontend:

```bash
cd frontend
npm install
npm run dev          # Vite dev server, proxying /api to a backend on :8095
npm run typecheck
npm run build
```

Contributor notes and hard rules for the ported duplicate-finder logic specifically are in [docker-music-dupes's original CLAUDE.md](https://github.com/mikestecker/docker-music-dupes/blob/main/CLAUDE.md) — the safety invariants listed there still apply unchanged to `app/modules/duplicate_finder/`.

---

## What's deliberately not built yet

Not missing — intentionally deferred, so the app isn't painted into a corner:

- A smart playlist (`.nsp`) editor that writes to `<music>/_playlists/`.
- Rebuilding the prompts library data from a new Apple Music export (porting the `generators/` pipeline).
- A log viewer for `update-navidrome-plugins.sh`.
- A UI for uploading a custom cover-art background (the API endpoint exists; there's no drag-and-drop uploader on the Cover art page yet, so it's host-filesystem-only for now).
- Sung-language filtering in Playlist Studio (needs a lyrics source and a language-ID library, neither of which exist in the toolkit yet) - a candidate addition if your library turns out to be meaningfully multilingual.
- Saved/reusable Alchemy anchors and scheduled "radios" (AudioMuse has real APIs for both, `/api/anchors` and `/api/radios` — Playlist Studio only does one-off Alchemy blends today).
- A full drag-and-drop layer editor for cover art (manual text/image positioning, closer to a design tool) — the current layout/font/style pickers cover the common cases; worth revisiting if that feels limiting.
- A library "health check" module that screens audio files for defects (clipping, truncation, loudness outliers) — unrelated to cover art, but a plausible future module alongside the duplicate finder.

**Permanently out of scope:** mounting the Docker socket into this app to let it `docker exec`/`docker restart` Navidrome for plugin updates. That would effectively give this app root on your NAS.

---

## License

[MIT](LICENSE)
