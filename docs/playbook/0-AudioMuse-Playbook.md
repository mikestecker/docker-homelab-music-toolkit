# AudioMuse Playbook

Oct 9, 2026 · @Mike Stecker

## Do these first

The scan is the expensive part, and it's done. These steps protect it and switch on the features that make AudioMuse worth having. The backup, Navidrome plugin and scheduling steps are in the teardown doc, so they're not repeated here.

1. **Pin the AudioMuse version.** AudioMuse's README warns that some major and minor releases change the analysis models and require a **new full analysis**. On `:latest`, one image pull could quietly put you back to a three-day scan.
   - Find your version in the UI footer, or run `sudo docker inspect audiomuse-flask --format '{{.Config.Image}}'`.
   - Change both `ghcr.io/neptunehub/audiomuse-ai:latest` lines to that exact tag, like `:3.6.1`.
   - From then on, read the [release notes](https://github.com/NeptuneHub/AudioMuse-AI/releases) before you bump it, and update the Navidrome plugin at the same time.
2. **Add an AI provider.** Instant Playlist (the type-a-sentence page) and AI playlist names only work with a language model behind them. **Don't run Ollama on the NAS**: it's already short on RAM. Pick one of these in **Setup Wizard → Advanced configuration → AI Provider & Playlist Naming**:
   - **Gemini:** set `AI_MODEL_PROVIDER=GEMINI` and paste a Google AI Studio API key, then change GEMINI\_MODEL\_NAME from the default gemini-2.5-pro to gemini-3-flash-preview. Flash is faster and is the Gemini model AudioMuse tested most recently. This is the setup in use.
   - **OpenAI-compatible:** use OpenRouter or a similar service with `AI_MODEL_PROVIDER=OPENAI`. AudioMuse's docs list `claude-sonnet-4.6` as the best cloud model they tested.
   - **Ollama** on another machine with a GPU, if you have one. Their officially supported model is `qwen3.5:9b`.

   Each request only sends your prompt and the tool plan. The model picks search tools, never song titles, so it can't invent tracks you don't own.
3. **Tune it for get-togethers.** In **Advanced configuration**:
   - `MAX_SONGS_PER_ARTIST_PLAYLIST`: change it from **5 to 2**. Five songs from one artist in an hour feels repetitive with a crowd.
   - `PLAYLIST_ENERGY_ARC`: turn it **on**. Instant Playlists then start gentle, build to a peak and wind down, instead of being shuffled by similarity.
   - `INSTANT_PLAYLIST_DEFAULT_N_RESULTS`: leave it at 50. Ask for longer lists in the prompt ("three hours of...").
4. **File AudioMuse's playlists in an AudioMuse folder.** That way they group together, and show as a folder in Feishin once its folder view ships (see the Organizing playlists tab). In **Advanced configuration**:
   - `SONIC_FINGERPRINT_CRON_PLAYLIST_NAME`: `AudioMuse/Sonic Fingerprint`
   - `ALBUM_OF_THE_WEEK_PLAYLIST_NAME`: `AudioMuse/Album of the Week`
   - Song Alchemy radios: put them in the `AudioMuse/Radios/` folder when you save the radio, for example `AudioMuse/Radios/Party Radio`.

   Cluster playlists are named by AudioMuse, so they get their folder from the cleanup script instead: set `RENAME_PREFIX=AudioMuse/Clusters/` in its `cleanup.env` (see Tuning clustering). It keeps the `_automatic` ending, which AudioMuse uses to find and replace last week's set.
5. **Optional: add Plex as a second music server.** Under **Setup → Music Servers**, add Plex with its token, then click **Align music servers** right away. It matches Plex's tracks to the ones already analyzed by file path and tags, with no downloads. Skip that step and the next nightly analysis downloads every Plex track to fingerprint it, which is a mini re-scan. Once aligned, AudioMuse playlists can go straight to Plexamp, where the family listens, as well as Navidrome.
6. **Raise clustering runs to 5000, then run Clustering once.** The field's tooltip recommends 5000, but the default is 1000. A run stops early once 60 runs in a row don't improve the best result, so 5000 is a ceiling, not a fixed cost.
   - **Change it permanently:** **Setup Wizard → Advanced configuration → Clustering & Playlist Generation**, set `CLUSTERING_RUNS` to `5000`, and save. AudioMuse stores it in its database and restarts the web app and workers itself, so there's nothing to change in TrueNAS. The scheduled Saturday run uses this saved value.
   - **The box on the Analysis page is for one run only.** **Clustering Runs** on the Basic tab is filled in from the saved value and applies only to the run you start there. If you change the box without changing the wizard, the next scheduled run goes back to 1000.
   - **Start the first run** from the Analysis page (Basic tab) with **Start Clustering**. Task Status shows progress like "Progress: 120/5000 runs. Active batches: 10. Best score: 4.52". Watch NAS memory during this first run.
   - **If memory gets tight,** lower `MAX_CONCURRENT_BATCH_JOBS` from `10` to `4`. This one isn't in the Setup Wizard. Add it as an environment variable on both the flask and worker containers in the TrueNAS app, then redeploy. Fewer batches at once is gentler on RAM than fewer runs.

### Clustering playlist names

In **Setup Wizard → AI Prompt**, set **Naming style** to **Full AI title** and replace the prompt with the one below. It follows the naming patterns from your own playlists:

- **Genre first** so the sidebar is easy to scan.
- **"Christian" plus the style** for Christian artists, and **"Worship" or "Hymns"** for praise music, at any energy. Faith words are only used when most of the playlist is faith music, never for mixed playlists.
- **Your real occasions, grouped by category (pickleball included),** including holidays and suggestive (not explicit) romance titles.

The AI only sees song titles and artist names, so the faith and genre calls depend on Gemini recognizing your artists. Click **Preview titles** after saving: it runs a quick clustering pass and shows the names without saving anything. If too many titles come out as workouts or parties, trim the occasion list. To allow more explicit romance titles, delete the "Keep these suggestive" line.

```
You are an expert music collector and MUST give a title to this playlist.
The title MUST start with the playlist's main genre or style, then the mood, activity or occasion it fits. Examples of the pattern: 'Country Pool Day', 'Classic Rock BBQ', 'Christian Rock Workout'.
Use a specific style when the songs share one (Classic Rock, Southern Rock, Red Dirt, Americana, Indie Folk, Trop Rock, Yacht Rock, Reggae, Soul, Synthwave, Grunge, Emo, Pop Punk, Ska, Metalcore, Celtic Punk, Lofi). Use a decade when the songs clearly share one ('90s Alt Road Trip'). If the songs mix styles, use the broad family (Rock, Indie, Country, Pop, Alternative).
When the songs are clearly from an older era, you MAY frame the title as nostalgia with Throwback, Jukebox or Dad Rock ('90s Alt Throwback', '2000s Pop Throwback', 'Millennial Dad Rock').
You MAY shorten words or use common alternate forms when it reads naturally, such as Alt for Alternative, Xmas for Christmas, Rock n Roll, Hip-Hop, Pop-Punk or Singalong. This is allowed, not required.
Faith music: if MOST songs are by Christian artists, start with 'Christian' plus the style ('Christian Hard Rock', 'Christian Indie', 'Christian Hip-Hop', 'Christian Ska'). If MOST songs are worship or praise songs, start with 'Worship'. If MOST are hymns, traditional or modern, start with 'Hymns', or 'Acoustic Hymns' or 'Instrumental Hymns' when that fits. Worship can be any energy, from soft and reflective to hype, dance and workout, so name it by the songs' real energy ('Worship Hype Workout', 'Worship Dance Party', 'Worship Quiet Morning'). NEVER use Christian, Worship, Hymns or other faith words when the playlist is mixed with secular songs.
Holidays: if most songs are holiday songs, name the holiday (Christmas, Easter, Fourth of July, New Year's, Halloween, Thanksgiving, Valentine's Day, St. Patrick's Day), for example 'Indie Christmas Fireside', 'Rock Fourth of July'.
Pick the occasion from when this music would really be played:
- Outdoors: pool days, laying out, beach days, boat and lake days, BBQs, front yard hangs, back porch evenings, campfires, yard work.
- Sports and fitness: workouts, running, bike rides, pickleball, game day, tailgates, skateboarding.
- On the move: road trips, night drives, Sunday drives, cruises and vacations.
- Around the house: house cleaning, garage projects, cooking, morning coffee, working from home, studying, rainy days.
- Social: dinner parties, game nights, happy hour, dive bar nights, birthday and graduation parties, family picnics, karaoke and singalongs.
- Faith: Sunday morning, pre-service hype, Bible study, prayer and quiet time, and youth group throwbacks. Use youth group ONLY for Christian music from the mid-90s to mid-2000s (the era of dc Talk, Newsboys, Jars of Clay, P.O.D., Relient K, Five Iron Frenzy, Switchfoot), as nostalgia: 'Christian Rock Youth Group Throwback', '90s Christian Youth Group'.
- Night: late nights, date nights, romance and the bedroom.
Say the occasion in your own words, 1 to 3 words. You do not have to copy the wording from the list above.
Faith playlists are not limited to the Faith group. Christian and Worship playlists can use ANY occasion above, including workouts, pickleball and other sports, pool days, drives, backyard hangs and upbeat jams around the house ('Christian Rock Pickleball', 'Worship Pool Day', 'Christian Pop Car Jams').
Romantic or sensual playlists are welcome, in any style: 'Country Bedroom Slow Jams', 'Rock Seduction', 'R&B Steamy Nights'. Keep these suggestive, not explicit.
Match the songs' real energy. Do NOT name a mellow or sad playlist after a party or workout, and do NOT name an energetic playlist calm or sleepy.
Vary your wording. Do not reuse the same occasion word across titles.
The title MUST use ONLY standard ASCII (a-z, A-Z, 0-9, spaces, and - & ' ! . , ? ( ) [ ]).
The title MUST be within the range of 5 to 40 characters long.
No special fonts or emojis.
* GOOD EXAMPLES: 'Country Pool Day', 'Classic Rock BBQ', 'Christian Rock Workout', 'Christian Hip-Hop Game Day', 'Worship Hype Drive', 'Red Dirt Road Trip', '90s Alt Throwback', 'Indie Kitchen Cleanup', 'Pop Punk Pickleball', 'Country Bedroom Slow Jams'
* BAD EXAMPLES: 'Sunset on the Porch' (No genre at the start)
* BAD EXAMPLES: 'Rock Songs Playlist', 'Upbeat Pop Mix' (Genre plus generic filler, says nothing about the moment)
* BAD EXAMPLES: 'Ambient Electronic Space - Electric Soundscapes - Emotional Waves' (Too long/descriptive)
* BAD EXAMPLES: '𝗝𝗂𝗈 𝗂𝗋𝗈𝗇𝗂 𝗉𝗋𝗈𝗇𝗂' (Non-standard characters)

CRITICAL: Your response MUST be ONLY the single playlist name. No explanations, no 'Playlist Name:', no numbering, no extra text or formatting whatsoever.
```

**Gemini needs billing turned on for this.** The free tier allows only 20 requests a day, and one preview or clustering run uses 10 or more. The Homelab project has $5 of prepaid credit with a $5 spend cap and auto-reload off. When the credit runs out, AudioMuse quietly falls back to tag names like `Rock_Pop_Indie_Medium...`. If those reappear, check the credit balance first.

AudioMuse strips anything outside plain ASCII from generated names and adds `_automatic` afterward, so a folder prefix can't come from this prompt. The cleanup script adds it.

## Tuning clustering

Clustering groups songs by sound alone. It never sees your genre tags or artist names, so it can't tell big-guitar worship from alt rock. That's how Passion and Hillsong UNITED ended up in a skate playlist next to Thrice. The settings below make clusters tighter, and a cleanup script removes the worship songs that still slip in.

### Settings to change

All of these are in **Setup Wizard → Advanced configuration**. Saving restarts AudioMuse on its own. Change one or two at a time, run Clustering, and compare.

| Setting | Wizard section | Default | Try | What it does |
| --- | --- | --- | --- | --- |
| `CLUSTERING_MAX_PLAYLIST_SONGS` | Clustering Auto-Calibration | 200 | 75 | The size auto-calibration aims for. A lower target makes it choose more, smaller clusters, and smaller clusters hold together better. With auto-calibration on, this is the setting that controls cluster count. Calibration overrides `NUM_CLUSTERS_MIN`/`MAX`, so leave those alone. |
| `MAX_DISTANCE` | Clustering & Playlist Generation | 0.5 | 0.4 | Songs farther than this from the middle of their cluster get dropped. This catches edge cases like a one-minute intro or a Dave Matthews song in a skate playlist. Below about 0.3, playlists start coming out too short. |
| `SCORE_WEIGHT_PURITY` | Clustering Scoring Weights | 1.0 | 2.0 | How much the search rewards playlists whose songs share a mood. The default favors playlists that differ from each other (`SCORE_WEIGHT_DIVERSITY`, 2.0) over playlists that hang together. |
| `SCORE_WEIGHT_OTHER_FEATURE_PURITY` | Clustering Scoring Weights | 0.0 | 0.5 | Adds consistency on danceable, aggressive, happy, party, relaxed and sad. A hard song and a soft one become less likely to share a playlist. |
| `MAX_SONGS_PER_ARTIST` | Clustering & Playlist Generation | 3 | 2 | Songs per artist in each cluster. The skate playlist had three each from Thrice and Thursday. This also applies to Instant Mix and other similar-song results. |
| `TOP_N_CLUSTERING_PLAYLIST` | Clustering & Playlist Generation | 10 | 15 | How many playlists to keep. Smaller clusters leave room for more of them. Each one costs a Gemini naming call. |
| `CLUSTERING_RUNS` | Clustering & Playlist Generation | 1000 | 5000 | See the clustering step in Do these first. |

Leave these on: `ENABLE_CLUSTERING_EMBEDDINGS` (clusters on the full audio fingerprint, the richer option), `CLUSTERING_AUTO_CALIBRATION`, and `CLUSTERING_CLEANING` (replaces last run's `_automatic` playlists, which the cleanup script expects).

Start with `CLUSTERING_MAX_PLAYLIST_SONGS` and `MAX_DISTANCE`. They make the biggest difference. Add the purity weights if clusters still mix hard and soft songs.

### Cleanup script for stray worship songs

`clean-clusters.py` goes through the `_automatic` playlists in Navidrome. It removes songs by artists in `worship-artists.txt`, but only when they make up a third or less of the playlist. A cluster that's mostly worship keeps them, so a "Worship Quiet Morning" cluster stays whole while the skate playlist loses its Passion songs. It's safe to run daily: AudioMuse rebuilds the playlists on each clustering run, and a playlist that's already clean is skipped.

**The artist list** has 228 artists turned on, in sections:

- The six you named.
- Worship bands, collectives and worship leaders: Elevation, Bethel, Maverick City, Hillsong, Passion, Brandon Lake, Phil Wickham and others.
- Hymn and liturgy projects from your Apple hymn playlists: Hope Hymns, Sojourn, Indelible Grace, Page CXVI.
- Instrumental and lofi worship.
- Adult-contemporary CCM like Big Tent Revival and The Kry: MercyMe, Casting Crowns, Steven Curtis Chapman.

A review section at the bottom is **off by default**. It holds artists who are worship or CCM but show up often in your rock and youth group playlists, like Crowder, Kings Kaleidoscope, Citizens, Third Day, Newsboys and TobyMac. Delete the `#` in front of any you want treated as worship. Christian rock, punk, metal and hip-hop artists like Switchfoot, Relient K, Thrice and Project 86 aren't on the list at all.

**Set it up**

1. Copy the three files (`clean-clusters.py`, `worship-artists.txt`, `cleanup.env.example`) to the NAS from your Mac, using your TrueNAS admin user:

   ```bash
   scp clean-clusters.py worship-artists.txt cleanup.env.example YOUR_ADMIN@10.0.9.101:/tmp/
   ```
2. On the NAS, move them into place and lock down the settings file:

   ```bash
   sudo mkdir -p /mnt/ssd-pool/apps/audiomuse/cluster-cleanup
   sudo mv /tmp/clean-clusters.py /tmp/worship-artists.txt /tmp/cleanup.env.example /mnt/ssd-pool/apps/audiomuse/cluster-cleanup/
   cd /mnt/ssd-pool/apps/audiomuse/cluster-cleanup
   sudo cp cleanup.env.example cleanup.env && sudo chmod 600 cleanup.env
   sudo nano cleanup.env
   ```
3. In `cleanup.env`, set `ND_USER` and `ND_PASS` to **the same Navidrome user AudioMuse uses** (it's under Setup → Music Servers in AudioMuse). Only a playlist's owner can edit it. Check that `ND_URL` uses your Navidrome port (4533 is the default).
4. Dry run. It lists every song it would remove and changes nothing:

   ```bash
   sudo python3 /mnt/ssd-pool/apps/audiomuse/cluster-cleanup/clean-clusters.py
   ```
5. If something on the WOULD list should stay, comment out that artist in `worship-artists.txt`. If something should go, add the artist. Run the dry run again.
6. Set `DRY_RUN=0` in `cleanup.env` and run it once by hand.
7. Schedule it: **System → Advanced Settings → Cron Jobs → Add**. Command `python3 /mnt/ssd-pool/apps/audiomuse/cluster-cleanup/clean-clusters.py`, run as `root`, daily at 6:00 AM, with Hide Standard Output checked. Running daily means you don't need to time it to the clustering schedule.

**Options in `cleanup.env`**

- `MAX_SHARE=0.34` is how big a share of a playlist listed artists can be before the playlist counts as worship and is left alone.
- `MIN_SECONDS=0` set to `90` also removes intros and interludes, like the one-minute Big Tent Revival intro.
- `RENAME_PREFIX=` set to `AudioMuse/Clusters/` files the cluster playlists in a folder. The `_automatic` ending stays, so AudioMuse still replaces them on its next run. See the Organizing playlists tab.
- Every run is logged to `clean-clusters.log` in the same folder. Once it passes 1 MB it's renamed to clean-clusters.log.1 and a new log starts, so the two together never go much past 2 MB.

**Commands for later changes.** Run these on the NAS. Start each session with:

```bash
cd /mnt/ssd-pool/apps/audiomuse/cluster-cleanup
```

Switch from dry run to live, or back:

```bash
sudo sed -i 's/^DRY_RUN=.*/DRY_RUN=0/' cleanup.env   # live
sudo sed -i 's/^DRY_RUN=.*/DRY_RUN=1/' cleanup.env   # dry run
```

Try a different setting for one run without editing the file:

```bash
sudo DRY_RUN=1 MAX_SHARE=0.5 MIN_SECONDS=90 python3 clean-clusters.py
```

Save a setting permanently (here, dropping tracks under 90 seconds):

```bash
sudo sed -i 's/^MIN_SECONDS=.*/MIN_SECONDS=90/' cleanup.env
```

Turn on an artist from the review section (removes the ` #  ` in front of it):

```bash
sudo sed -i 's/^# Crowder$/Crowder/' worship-artists.txt
```

Add a new artist, or turn one off:

```bash
echo "Rend Collective" | sudo tee -a worship-artists.txt >/dev/null   # add
sudo sed -i 's/^Lauren Daigle$/# Lauren Daigle/' worship-artists.txt  # turn off
```

Check whether an artist is on the list (lines starting with `#` are off):

```bash
grep -in "hillsong" worship-artists.txt
```

Read the log:

```bash
sudo tail -n 50 clean-clusters.log        # latest runs
sudo grep -E "CLEAN|WOULD" clean-clusters.log | tail -n 20   # only playlists it changed
```

For bigger edits, open the file in nano (save with Ctrl+O then Enter, exit with Ctrl+X):

```bash
sudo nano worship-artists.txt
```

It only cleans the Navidrome copies. If you add Plex as a second server, AudioMuse makes separate playlists there that this script doesn't touch. Titles are set before cleanup, so a title still reflects the songs that were removed.

## Features at a glance

Every page saves its result as a playlist on your server. Use the first three most for get-togethers.

| Page | What it does | Reach for it when |
| --- | --- | --- |
| **Instant Playlist** | Turns a sentence into a playlist. The AI picks search tools; real queries pick the songs. Needs an AI provider | You can describe the event: "pool party, 3 hours, no rap" |
| **Song Alchemy** | Blends songs, artists or moods you **Include**, minus ones you **Exclude**. Saves as an anchor or a weekly-refreshed radio | You know 3 or 4 songs that nail the vibe and want 50 more like them |
| **Song Path** | Builds a smooth bridge between two songs | Shaping a night: chill arrival song to peak-party song |
| **Similar Song** | Songs that sound like one track. Same engine as Navidrome's Instant Mix | Quick "more like this" |
| **Text Search** | Finds songs by how they *sound*, from a short description | "upbeat country guitar" |
| **Lyrics Search** | Finds songs by what they're *about*: by axis, free text, or a song with similar meaning | Theme playlists: summer, road trips, hometowns |
| **Sonic Fingerprint** | Your most-played songs plus new matches for your taste. Uses Navidrome play history | A personal mix that grows with your listening |
| **Clustering** | Automatic mood and genre playlists across the whole library | Discovering corners of your library |
| **Music Map** / **Hyperbolic Explorer** | Your library drawn as a 2D map, and a browsable genre/mood tree | Exploring and spotting forgotten albums |
| **Album Creation** | Builds a cohesive 12-track "album" from a song or description; also runs as Album of the Week | Something to put on start to finish |

Search by Recording (a Shazam-style lookup) stays hidden, because Neural Fingerprint is off. You don't need it for any of the above.

## Writing prompts

The three text boxes read your words in completely different ways, so the same phrase can work in one and flop in another.

### Text Search: short sound descriptions

It compares your words to the *audio*, using a model trained on sound paired with descriptions. It knows nothing about titles, artists, years or lyrics.

- **Use 2 to 4 words:** genre, instrument, then mood. Genre and instrument are the strongest signals. Mood is the weakest.
- **Use words a sound engineer would use:** acoustic guitar, electric guitar, piano, organ, synth, bass, female vocal, raspy voice, harmonized vocals, energetic, groovy, mid-tempo.
- **Avoid** negations ("no rap" gets read as *rap*), artist names, decades and long sentences.

| Weak | Better |
| --- | --- |
| songs for a pool party in the summer | upbeat summer pop |
| 90s rock but not grunge | energetic rock guitar |
| something like Zac Brown Band | acoustic country singalong |
| no screaming, chill | mellow acoustic guitar |

### Lyrics Search: what the song is about

- **By Text:** describe a theme, situation or story, not a sound. "Driving with the windows down on a summer night" beats "upbeat driving songs".
- **By Axis:** pick values from the five dropdowns (setting, social dynamic, emotional valence, time, weight). It's the most predictable mode, because the vocabulary is fixed. Start with one or two axes, then add more to narrow.
- **By Song:** pick a song whose *meaning* you like. Results blend lyrics (75%) with sound (25%), so they stay musically plausible.

### Instant Playlist: full sentences

This is the one place to write like you'd talk. The AI turns your sentence into a plan, and code pulls these straight out of your words even when the model misses them:

- **Size:** "40 songs", or a time with "long" or "of" right after it: "two hours long", "three hours of". A bare "two hours," is ignored. A size in the prompt overrides the Number of songs box, which only counts when the prompt names no size (default 50, up to 200). Times are trimmed to your real track lengths.
- **Era:** "90s", "early 2000s", "last 5 years", "recent".
- **Tempo and energy:** "upbeat", "chill", "over 120 BPM", "energetic but not intense".
- **Limits:** "max 2 songs per artist", "one song per artist".
- **Exclusions:** "no rap", "no live versions", "no remixes". This is the only place negation works.
- **Recently added:** surfaces your new Tidarr downloads.
- **Seeds:** "like Tom Petty", "like Brooks & Dunn but more upbeat". The artist has to be in your library.
- **Journeys:** "from Fleetwood Mac to Foo Fighters" walks between the two in order.

Tips:

- **Use genre words it knows**, like rock, pop, country, classic rock, alternative, indie, folk, soul, funk, punk, hard rock and dance. It also takes sound words like dreamy or dark.
- **Say "instrumental", not "no vocals".** A negation-only description gets dropped.
- **Open "what the AI decided"** under the results. If a genre or decade got missed, rephrase that part. Don't just retry the same prompt.
- **Don't count on explicit-lyrics filtering.** There's no clean/explicit field, so preview anything headed for a crowd with kids.

## Sample prompts

These are written for a crowd-pleasing library: country, classic rock, rock, pop and alternative from the 90s on, with light rap. Copy them, then swap in your own artists and lengths.

For rebuilding your old Apple Music playlists, see Recreating playlists and the 65 recipes in Playlist recipes.

### Instant Playlist

| Occasion | Prompt |
| --- | --- |
| Pool party | Pool party: three hours of upbeat, danceable pop, country and rock from the 2000s to today, max 2 songs per artist, no rap, no live versions |
| Backyard BBQ | Backyard BBQ singalongs: classic rock and 90s alternative everyone knows, energetic but not heavy, 60 songs, one song per artist |
| Game night | Game night background: feel-good mid-tempo pop and rock that won't take over the conversation, two hours long, max 2 per artist |
| Guests arriving | First hour of a party: relaxed, warm acoustic and soft rock that slowly picks up energy, 15 songs |
| Peak of the night | High energy party anthems, rock and pop over 120 BPM, 30 songs, no ballads |
| Country night | Upbeat country from the last 10 years, good for a crowd, 40 songs, no live versions |
| Wind down | After the guests leave: mellow acoustic songs, calm, 45 minutes long |
| Seeded | Songs like Tom Petty and The Killers but more upbeat, 30 songs |
| Journey | From Fleetwood Mac to Foo Fighters, 25 songs |
| New stuff | Recently added rock and alternative, 30 songs, one song per artist |
| Work focus | Instrumental, calm, steady tempo, two hours long |
| Workout | High energy rock and pop over 125 BPM, one hour long |

### Text Search

Two to four words each:

- upbeat summer pop
- acoustic country singalong
- classic rock guitar solo
- energetic punk rock
- funky bass groove
- smooth female vocal soul
- mellow piano ballad
- harmonized vocals folk
- groovy electric guitar
- raspy male vocal rock

### Lyrics Search: By Text

- summer nights with friends
- driving on an open road with the windows down
- a Friday night out after a long week
- growing up in a small hometown
- falling in love for the first time
- dancing until the sun comes up
- coming home after being away

## Everyday use

### Instant Mix in your players

Once the Navidrome plugin has its API URL and token, **Instant Mix** on any song in Navidrome or Feishin runs AudioMuse's Similar Song behind the scenes. **Artist Radio** and the similar-artists list do the same. In Symfonium, turn on **Use similar tracks for Radio Mix**. Music Assistant reads Navidrome, so mixes and saved playlists work on the whole-house speakers too.

### Recipe: a party radio that refreshes itself

1. Open **Song Alchemy**. **Include** 4 or 5 songs that are exactly the vibe, from different artists.
2. **Exclude** one or two slow songs or ballads you know you don't want. That pushes results away from that sound.
3. Leave **temperature** at 1.0 for variety, or drop it to around 0.5 for a tighter, more predictable list. Set results to 60.
4. Check the 2D plot. Kept songs should cluster near your includes. Then save it as an **anchor**.
5. Turn the anchor into a **radio**. The scheduled Radio Playlists task rebuilds it in place, so "Party Radio" stays one playlist that keeps refreshing as Tidarr adds albums.

### Recipe: shape the night with Song Path

Pick a mellow arrival song and the biggest singalong you own, and run **Song Path** between them with about 25 songs. Turn on **fix size** if you want exactly that many. Play it from the start as guests arrive and it'll climb toward the peak on its own. Instant Playlist does the same thing if you write "from X to Y".

### Recipe: fix a playlist that's almost right

- **Too samey:** lower the per-artist cap in the prompt ("one song per artist"), or raise Alchemy's temperature.
- **Wandering off-genre:** name the genre explicitly in Instant Playlist, or add a seed song from that genre to Alchemy's includes.
- **One wrong song keeps showing up:** add it, or its artist, as an Alchemy **Exclude**.

### Let it run on its own

- **Sonic Fingerprint (Saturday):** your top Navidrome plays plus new matches. It improves as you listen through Navidrome and Feishin.
- **Album of the Week (Saturday):** a cohesive 12-track "album" built from your library.
- **Clustering (Saturday):** fresh mood playlists, with AI names once a provider is set.
- **Nightly analysis:** keeps all of the above current as the Tidarr backlog lands.

Sources: [AudioMuse-AI README](https://github.com/NeptuneHub/AudioMuse-AI), [ALGORITHM.md](https://github.com/NeptuneHub/AudioMuse-AI/blob/main/docs/ALGORITHM.md) (Text Search, Lyrics Search, Instant Playlist, Song Alchemy chapters), [PARAMETERS.md](https://github.com/NeptuneHub/AudioMuse-AI/blob/main/docs/PARAMETERS.md), [MULTI\_SERVER.md](https://github.com/NeptuneHub/AudioMuse-AI/blob/main/docs/MULTI_SERVER.md)
