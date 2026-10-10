# Organizing playlists

Oct 9, 2026

Navidrome can't put playlists in folders yet, so the plan for now is a naming convention: `Folder/Subfolder/Playlist`. Feishin's upcoming folder view turns those names into folders, every other app sorts them together, and they convert cleanly to real folders once Navidrome supports them.

## Where things stand

Real folders depend on a shared API standard that hasn't been agreed yet, so a name-based convention is the only thing that works today.

| Piece | Status | What it means for you |
| --- | --- | --- |
| Navidrome server | No playlist folders. Its maintainer says folders will come in Navidrome's new web UI, and that client support waits until OpenSubsonic agrees on an API ([#5325](https://github.com/navidrome/navidrome/discussions/5325), [#3371](https://github.com/navidrome/navidrome/discussions/3371)). | Nothing to switch on yet. |
| OpenSubsonic proposal | A `playlistFolders` extension is proposed ([PR #255](https://github.com/opensubsonic/open-subsonic-api/pull/255)): nested folders per user, new calls to create, rename, delete and list folders, and a `movePlaylist` call to file a playlist. Filing a playlist doesn't change the playlist itself, and apps that don't know about folders still see every playlist. Ampache already has something similar; Koel is the reference. | Not merged. When it is, and Navidrome adopts it, your names can be turned into real folders by a script. |
| Feishin | A pull request adds client-side folders built from `/` in playlist names ([PR #2017](https://github.com/jeffvli/feishin/pull/2017)). You turn it on in Settings, General, Sidebar, Enable folders. There are three views: single folder, a navigation view with a back button, and a tree with unlimited nesting. It only changes Feishin's display, nothing on the server. | Not merged yet. Once it ships, the convention below shows up as folders in Feishin's sidebar. |
| Every other app | Navidrome's web UI, Symfonium, Music Assistant and the rest show the full name in a flat list. | A shared prefix still keeps each folder's playlists sorted together. |

## The naming convention

- **`Folder/Playlist` or `Folder/Subfolder/Playlist`.** Two levels at most. It stays readable in flat lists, and Feishin's single-folder view only groups by the first part anyway.
- **No spaces around the slash.** `Occasions/Pool Day`, not `Occasions / Pool Day`. That matches Feishin's examples, like `Style/Phonk House`.
- **Folder names are fixed words.** Use the exact folder names in the next section so everything sorts together. One spelling, one capitalization.
- **Emoji go at the end, if at all.** A name that starts with an emoji sorts away from its folder, so `🤖 Sonic Fingerprint` becomes `AudioMuse/Sonic Fingerprint`. This replaces the 🤖 and 📥 prefixes used elsewhere in this doc.
- **Keep names unique.** Two playlists with the same full name make renames ambiguous, so the rename script skips them.
- **Some names you can't control.** NaviBeat mixes and the ListenBrainz daily playlist are named by their plugins, so they stay at the top level.

## Your folders

Nine top-level folders. Three hold playlists that fill themselves (Smart, AudioMuse, Imports), and six hold what you build and keep. It follows the layout from the Navidrome discussion (smart lists, imports, events, seasonal) and adds the moods and occasions your recipes are built around.

```
Smart/            Recently Added, Favorites, Forgotten Favorites, 90s Music ...
  Artists/        dc Talk, Skillet, Thrice ...
AudioMuse/        Sonic Fingerprint, Album of the Week
  Clusters/       the weekly _automatic playlists
  Radios/         saved Song Alchemy radios
Imports/
  Tidarr/         playlists downloaded through Tidarr
Occasions/
  Summer/  Parties/  Workouts/  Road/  Around the House/
Faith/
  Worship/  Hymns/  Christian Rock/  Christian Pop/  Christian Hip-Hop/
Moods/
  Chill/  Hype/  Rainy Day/  Date Night/
Eras/
  80s/  90s/  2000s/
Seasonal/
  Christmas/  Halloween/  Fourth of July/  St. Patrick's/
Curated/
  Keepers/  Events/  Setlists/
```

| Folder | What goes in | How playlists get there |
| --- | --- | --- |
| Smart | The `.nsp` smart playlists | Rename script, once |
| AudioMuse | Sonic Fingerprint, Album of the Week, clusters, radios | AudioMuse settings and the cleanup script, automatically |
| Imports/Tidarr | Playlists Tidarr downloads | Tagging script, daily |
| Occasions | Saved runs from Summer and water, Parties and backyard, Workouts and sports, plus Red Dirt Road Trip, Classic Rock Road Trip and Country Morning Coffee | You, when you save a run |
| Faith | Saved runs from Christian rock eras, Modern Christian, and Worship and hymns | You |
| Moods | Date night and bedroom recipes, Indie Rainy Day, Americana Back Porch, Synthwave Night Drive | You |
| Eras | 90s Alt Throwback, Millennial Dad Rock, Millennial Throwback Party, the new library's 80s and 90s Night | You |
| Seasonal | Holiday recipes and Fourth of July | You |
| Curated | Playlists you made by hand: keepers, dated events ("Curated/Events/Office Party 2025"), concert setlists | You |

Saved runs need the full name typed when you save. For example, save a Country Pool Day run as `Occasions/Summer/Country Pool Day`, or a dated one as `Occasions/Summer/Pool Day 2026-07-04`.

## Put it in place

Navidrome keeps a playlist's name when it re-reads the `.m3u` or `.nsp` file behind it, so renaming in Navidrome is permanent. The new `rename-playlists.py` script does the renames from a plain text map, `playlist-folders.txt`. The map comes pre-filled with your smart playlists and AudioMuse's fixed playlists. The script uses the same `navidrome.env` as the Tidarr tagging script.

1. Copy the files to the NAS from your Mac. The updated `clean-clusters.py` and `cleanup.env.example` add the cluster folder option used in step 4, and the updated tagging script now defaults to the Imports/Tidarr/ prefix.

   ```bash
   scp rename-playlists.py playlist-folders.txt tag-tidarr-playlists.py clean-clusters.py cleanup.env.example truenas_admin@10.0.9.101:/tmp/
   ```
2. Put them in place:

   ```bash
   sudo mv /tmp/rename-playlists.py /tmp/playlist-folders.txt /tmp/tag-tidarr-playlists.py /mnt/ssd-pool/apps/navidrome/scripts/
   sudo mv /tmp/clean-clusters.py /tmp/cleanup.env.example /mnt/ssd-pool/apps/audiomuse/cluster-cleanup/
   ```
3. Rename the smart and AudioMuse playlists. See what you have, edit the map if needed, do a dry run, then apply:

   ```bash
   cd /mnt/ssd-pool/apps/navidrome/scripts
   sudo python3 rename-playlists.py --list
   sudo nano playlist-folders.txt
   sudo python3 rename-playlists.py
   sudo python3 rename-playlists.py --apply
   ```

   It skips any rename that would collide with an existing name and tells you. Running it again is safe.
4. File the weekly cluster playlists under AudioMuse/Clusters. The cleanup script adds the prefix and keeps the `_automatic` ending, which AudioMuse matches on to replace last week's set:

   ```bash
   cd /mnt/ssd-pool/apps/audiomuse/cluster-cleanup
   sudo grep -q '^RENAME_PREFIX=' cleanup.env || echo 'RENAME_PREFIX=' | sudo tee -a cleanup.env >/dev/null
   sudo sed -i 's|^RENAME_PREFIX=.*|RENAME_PREFIX=AudioMuse/Clusters/|' cleanup.env
   sudo python3 clean-clusters.py
   ```

   The dry run shows WOULD lines for the renames. They happen on the next live run, so new clusters get filed within a day of each clustering run.
5. Point AudioMuse's fixed playlists at the new names, so it keeps updating the same playlists. In **Setup Wizard → Advanced configuration**, set `SONIC_FINGERPRINT_CRON_PLAYLIST_NAME` to `AudioMuse/Sonic Fingerprint` and `ALBUM_OF_THE_WEEK_PLAYLIST_NAME` to `AudioMuse/Album of the Week`. For new Song Alchemy radios, name them `AudioMuse/Radios/Party Radio` and so on. Re-save any existing 🤖 radios under the new names, since a rename in Navidrome alone could be overwritten when the radio refreshes.
6. Move the Tidarr playlists from the 📥 prefix to the Imports folder, then change the daily cron job to use the new prefix:

   ```bash
   cd /mnt/ssd-pool/apps/navidrome/scripts
   sudo python3 tag-tidarr-playlists.py --undo --prefix "📥 " --apply
   sudo python3 tag-tidarr-playlists.py --prefix "Imports/Tidarr/" --apply
   ```

   To file new Tidarr playlists automatically, add a second daily cron job next to the cleanup one: **System → Advanced Settings → Cron Jobs → Add**, command `python3 /mnt/ssd-pool/apps/navidrome/scripts/tag-tidarr-playlists.py --apply`, run as `root`, daily (6:15 AM works, just after the cleanup job), with Hide Standard Output checked. Without it, you rerun the second command above whenever you've imported new Tidarr playlists.
7. Give new smart playlists their folder from the start. In a new `.nsp` file, set `"name": "Smart/Workout Favorites"`.
8. When Feishin ships the folder view, turn on **Settings → General → Sidebar → Enable folders** and pick the tree view, which shows both levels.

## Folders as playlists

A different idea from [Flemming's blog](https://flemmingss.com/use-folders-as-playlists-in-navidrome/) (2022): instead of putting playlists in folders, turn a folder of loose tracks into a playlist. Navidrome is built around albums, so a folder of single tracks (say, `individual_tracks/rock/`) is hard to browse. The article writes an `.m3u` per folder with a Windows batch script, which you rerun after every change.

You don't need the script. A smart playlist with a file path rule does the same job, stays up to date by itself, and runs on the NAS:

```json
{
  "name": "Smart/Folders/Rock Singles",
  "all": [{ "contains": { "filepath": "individual_tracks/rock/" } }],
  "sort": "title"
}
```

Save it in `_playlists` with the same steps as the other smart playlists. This is mostly useful for loose singles. Your Tidarr albums are already organized by album, so the recipes and folders above cover them better.

## When real folders arrive

If OpenSubsonic approves `playlistFolders` and Navidrome adopts it, a one-time script can turn every name into a real folder. It would read each playlist's path, create the folders with `createPlaylistFolder`, file each playlist with `movePlaylist`, and strip the prefix from the name. Under the proposal, folders belong to each user and filing doesn't change the playlist, so the other apps in the house keep seeing everything. Navidrome's maintainer has also said its new web UI will have folders, so watch the Navidrome release notes.

## Sources

- [Organization for playlists, Navidrome discussion #5325](https://github.com/navidrome/navidrome/discussions/5325)
- [Folders for playlists, Navidrome discussion #3371](https://github.com/navidrome/navidrome/discussions/3371)
- [Playlist folders in the sidebar, Feishin PR #2017](https://github.com/jeffvli/feishin/pull/2017)
- [playlistFolders extension, OpenSubsonic API PR #255](https://github.com/opensubsonic/open-subsonic-api/pull/255)
- [Use folders as playlists in Navidrome, Flemming's blog (Oct 2022)](https://flemmingss.com/use-folders-as-playlists-in-navidrome/)
- Navidrome source (`core/playlists/import.go`): a re-imported playlist keeps its stored name.
- AudioMuse source (`tasks/mediaserver/__init__.py`): old cluster playlists are found by names ending in `_automatic`.
