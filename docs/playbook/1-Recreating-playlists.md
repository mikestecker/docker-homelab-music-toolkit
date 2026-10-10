# Recreating your Apple Music playlists

Oct 9, 2026

The goal is close in feel, not an exact copy. Every playlist of your own has a ready-made song-list prompt, occasions have concept recipes, and smart playlists and artist radio cover the rule-based and single-artist ones.

## What's in the export

Your export (Oct 1, 2026) has 758 playlists and 223,313 song entries. Only about two thirds are playlists you'd want back, and each kind has a different best method.

| Kind | Count | What it is | Best method |
| --- | --- | --- | --- |
| Your own mixes | 494 | Occasion, mood and genre playlists, including ones you saved from other users | Song-list prompts (489 have one), or a concept recipe (326 are covered by the 65 recipes) |
| Single-artist | 163 | 60% or more of the songs are one artist ("Chris Renzema 2024", "Bob Marley", "Copeland: The Ultimate Playlist") | Artist radio |
| Editorial and setlists | 39 | Essentials, Next Steps, "Inspired by", tour and concert setlists ("Emery at Sloss Furnaces") | Artist radio, or Song Alchemy with the setlist's songs |
| Smart playlists | 35 | Apple rules: Recently Added, Top 25 Most Played, 90's Music, plus one per artist (dc Talk, Skillet, Thrice) | Navidrome smart playlists |
| Housekeeping | 23 | \_All Songs, Needs Artwork, Purchased AAC, "Playlist 4", tests | Skip |
| Folders and empty | 4 | Apple folders (Christmas) and one empty list | Skip |

The export has no genre field, so genre in the recipes comes from the playlist names and the artists in them.

## Pick a method

The methods run from exact to loose. The closer you need it to the original, the higher up the table you start.

| Method | How close to the original | Effort | Changes over time | Use it for |
| --- | --- | --- | --- | --- |
| 1. Song-list prompt | Same feel, built from five of its own songs | Copy and paste | Every run | Any specific playlist you miss |
| 2. Save and grow | Keeps a good run, then makes more like it | A minute | When you rerun it | Runs that came out right |
| 3. Smart playlist | Same rule, your current library | One small file each | Yes, every scan | Recently added, most played, favorites, a decade, one artist |
| 4. Artist radio | Same artist, different picks | Seconds | Every time | Single-artist, Essentials and Next Steps lists |
| 5. Concept recipe | Same occasion and feel, across several playlists | One prompt | Every time | Pool days, workouts, BBQs, holidays, date nights |
| 6. Clustering | Whatever AudioMuse finds by sound | None, it runs on a schedule | Each run | Discovering groupings, not recreating specific lists |

A good order: for a playlist you miss, open its song-list prompt. For an occasion, use a recipe. Whenever a run comes out right, save it (method 2).

## 1. Song-list prompts

489 of your own mixes each have ready-made prompts in [Apple Playlist Prompts](https://claude.ai/artifact/MMzcxwF7EuMChkhnAwa8EU). Search for a playlist, open it, and copy one of three versions.

| Version | Where to paste it | Example (Youth Group Throwback) |
| --- | --- | --- |
| Instant Playlist | Instant Playlist | Songs like Supernatural by DC Talk, Your Love Oh Lord (Psalm 36) by Third Day, Entertaining Angels by Newsboys, Made To Love by TobyMac, We're A Band by Audio Adrenaline, mostly 90s and 2000s, Christian artists only, 185 songs, max 2 songs per artist, no live versions |
| Journey | Instant Playlist | From Supernatural by DC Talk to We're A Band by Audio Adrenaline, 60 songs |
| Song Alchemy seeds | Song Alchemy, under Include | 12 songs from across the playlist, in order |

**How the songs were picked.** Each playlist is cut into equal slices, in order. From each slice the script takes the song by the artist who shows up most in that playlist, breaking ties by how many of your playlists the song is on. That keeps the picks on the playlist's core sound and spreads them from start to finish. One song per artist. Live versions, remixes, interludes and (outside holiday playlists) Christmas songs are skipped, and tags like "(2012 Remaster)" and "feat." guests are stripped from titles.

**What AudioMuse does with a song list.** These limits come from the AudioMuse source code:

- **Five songs is the useful maximum.** Instant Playlist makes at most 4 searches per request, with at most 5 seed songs per search. Paste a list of 50 songs and most of it gets dropped, so each prompt names five. Song Alchemy takes more, up to 16, which is why its list is longer.
- **Names don't have to match exactly.** AudioMuse looks a seed up exactly first, then ignoring spacing and punctuation, then by fuzzy similarity. A Tidal title that differs a little from Apple's still resolves. A song you don't own at all is skipped, and the other seeds still work.
- **Order isn't kept.** AudioMuse orders the result itself, by tempo, energy and key. If the playlist's arc matters, use the Journey version, which walks from the opening song's sound to the closing one.
- **The seed songs themselves aren't in the result.** You get songs like them. Add a seed back by hand if you want it in.
- **200 songs at most** per Instant Playlist, so longer playlists ask for 200.
- **Faith playlists** (185, flagged by name or by their artists) say "Christian artists only", and Christmas playlists say "Christmas songs only".

**Which version to use.** Start with Instant Playlist. If it wanders off the sound, switch to the Alchemy seeds, which stay closest to the original. Use the Journey for playlists that build up or wind down. Five playlists had too few usable songs and have no prompts.

## 2. Save and grow

A prompt gives different results each run, so save a run you like before you lose it. Then use it as the seed for more.

1. When a run comes out right, save it as a playlist in Navidrome. Use the old name if you like it ("Pool Tunes"), since AudioMuse's own playlists carry the 🤖 prefix.
2. Trim anything that doesn't fit. A few minutes of deleting does more than rewording the prompt.
3. For more like it later, open **Song Alchemy** and add the saved playlist as an input. Alchemy accepts whole playlists, not just songs and artists.
4. In Alchemy, save the run as an anchor so you can rerun the same blend later as a radio.

From any song in that playlist, **Instant Mix** in Navidrome also gives you a quick radio built on its sound.

## 3. Smart playlists

About 15 of your Apple smart playlists are worth keeping, and Navidrome can rebuild them as rules that update themselves. No AI is involved, so these are exact and predictable.

**How they work.** A smart playlist is a small JSON file ending in `.nsp`. They go in a `_playlists` folder inside your library (`/mnt/tank/media/music/_playlists`), owned by 3000:3000 like the rest of your apps. Navidrome picks them up on a library scan and refreshes them whenever you open them. You can't edit them in the Navidrome web UI yet, so you change the file and rescan. They belong to the first admin user, and rules about plays and favorites use that user's history.

| Apple smart playlist | Navidrome rule |
| --- | --- |
| Recently Added | Added in the last 60 days, newest first |
| Recently Played | Played in the last 30 days |
| Top 25 Most Played | Highest play count, 25 songs |
| Least Recently Played | Favorites you haven't played in 6 months |
| My Top Rated | Your favorites (you use favorites, not ratings) |
| 90's Music | Year 1990 to 1999 |
| Christmas Songs | Genre contains Christmas |
| dc Talk, Skillet, Thrice and 13 more | Artist contains the name |
| \_All Songs, Needs Artwork, Purchased AAC, Music Videos | Skip, Apple-only housekeeping |

**Create them.** SSH into the NAS and paste each block in order.

1. Make the folder and go into it:

   ```bash
   DIR=/mnt/tank/media/music/_playlists
   sudo mkdir -p "$DIR"
   cd "$DIR"
   ```
2. Write the seven rule-based playlists:

   ```bash
   sudo tee "Recently Added.nsp" >/dev/null <<'EOF'
   {
     "name": "Recently Added",
     "all": [{ "inTheLast": { "dateadded": 60 } }],
     "sort": "dateadded",
     "order": "desc",
     "limit": 200
   }
   EOF
   
   sudo tee "Recently Played.nsp" >/dev/null <<'EOF'
   {
     "name": "Recently Played",
     "all": [{ "inTheLast": { "lastplayed": 30 } }],
     "sort": "lastplayed",
     "order": "desc",
     "limit": 100
   }
   EOF
   
   sudo tee "Top 25 Most Played.nsp" >/dev/null <<'EOF'
   {
     "name": "Top 25 Most Played",
     "all": [{ "gt": { "playcount": 0 } }],
     "sort": "playcount",
     "order": "desc",
     "limit": 25
   }
   EOF
   
   sudo tee "Forgotten Favorites.nsp" >/dev/null <<'EOF'
   {
     "name": "Forgotten Favorites",
     "all": [
       { "is": { "loved": true } },
       { "notInTheLast": { "lastplayed": 180 } }
     ],
     "sort": "random",
     "refreshDelay": "24h",
     "limit": 50
   }
   EOF
   
   sudo tee "Favorites.nsp" >/dev/null <<'EOF'
   {
     "name": "Favorites",
     "all": [{ "is": { "loved": true } }],
     "sort": "dateloved",
     "order": "desc",
     "limit": 500
   }
   EOF
   
   sudo tee "90s Music.nsp" >/dev/null <<'EOF'
   {
     "name": "90s Music",
     "all": [{ "inTheRange": { "year": [1990, 1999] } }],
     "sort": "random",
     "refreshDelay": "24h",
     "limit": 200
   }
   EOF
   
   sudo tee "Christmas Songs.nsp" >/dev/null <<'EOF'
   {
     "name": "Christmas Songs",
     "any": [
       { "contains": { "genre": "Christmas" } },
       { "contains": { "genre": "Holiday" } }
     ],
     "sort": "random",
     "refreshDelay": "24h"
   }
   EOF
   ```

   `refreshDelay` keeps the three shuffled playlists fixed for 24 hours. Without it, Navidrome rebuilds a smart playlist every time a client opens it, after only 5 seconds by default. A random playlist then reshuffles mid-listen, and Forgotten Favorites drops each song as soon as you play it, because playing it makes it no longer forgotten.
3. Write one playlist per artist. Add or remove names inside the parentheses to change the list:

   ```bash
   ARTISTS=("dc Talk" "Jars of Clay" "Jon Foreman" "Blindside" "Muse" "Mute Math" "MxPx" "NEEDTOBREATHE" "P.O.D." "Project 86" "Radiohead" "Skillet" "Smashing Pumpkins" "The Beatles" "Thrice" "U2")
   for a in "${ARTISTS[@]}"; do
     printf '{\n  "name": "%s",\n  "all": [{ "contains": { "artist": "%s" } }],\n  "sort": "year,album,tracknumber"\n}\n' "$a" "$a" | sudo tee "$a.nsp" >/dev/null
   done
   ```
4. Set the owner and permissions, then check that every file is valid JSON:

   ```bash
   sudo chown -R 3000:3000 "$DIR"
   sudo chmod 755 "$DIR"
   sudo chmod 644 "$DIR"/*.nsp
   for f in "$DIR"/*.nsp; do python3 -m json.tool "$f" >/dev/null && echo "OK   $f" || echo "BAD  $f"; done
   ```

   Every line should start with OK. A BAD line means that file has a typo, usually a missing comma or quote.
5. Wait about a minute. Navidrome's folder watcher notices the new files and adds the playlists without a full scan. You can confirm it in the log:

   ```bash
   sudo docker logs --since 5m navidrome 2>&1 | grep -E "_playlists|synced playlist"
   ```

   You should see one "Adding synced playlist" line per file. If nothing shows up after a few minutes, run **Quick Scan** from the Navidrome web UI (the activity icon at the top right, as an admin). Don't start a scan while another one is running, and skip Full Scan for this. A full scan rereads your whole library and took 17 minutes last time.

**Change one later.**

```bash
sudo nano "/mnt/tank/media/music/_playlists/90s Music.nsp"
```

In nano, save with Ctrl+O, then Enter, and exit with Ctrl+X. The watcher picks up the change within a minute, and the new rules apply the next time you open the playlist.

**Remove one.** Delete the file, wait a minute, then delete the playlist in Navidrome too, since removing the file doesn't always remove the playlist:

```bash
sudo rm "/mnt/tank/media/music/_playlists/U2.nsp"
```

Two checks: the Christmas rule only works if your files have a Christmas or Holiday genre tag, and if an artist rule comes back empty, try `albumartist` in place of `artist`. Smart playlists are still marked beta in Navidrome ([docs](https://www.navidrome.org/docs/usage/features/smart-playlists/)).

## 4. Artist radio

Your 202 single-artist, Essentials and setlist playlists don't need recipes. They're one artist, and AudioMuse already does that well.

| Kind of playlist | Example from your export | What to use |
| --- | --- | --- |
| One artist, the hits | Bob Marley Essentials, Best of Lifehouse | Artist Radio in Navidrome, or an artist smart playlist (method 3) |
| One artist, deep cuts | All Kings Kaleidoscope All The Time, Chris Renzema 2024 | Song Alchemy with 3 or 4 of that artist's songs. Expect similar artists mixed in, since AudioMuse caps songs per artist. |
| Artist plus friends | Kings K + Friends, Project 86/POD/Blindside | Instant Playlist: "Songs by Project 86, P.O.D. and Blindside and similar bands, 40 songs" |
| Next Steps (artists they influenced) | Beck: Next Steps, Death Cab for Cutie: Next Steps | Instant Playlist: "Artists like Death Cab for Cutie, no Death Cab for Cutie, 30 songs, one song per artist" |
| Concert setlists | Emery at Sloss Furnaces, Blindside at Sloss Furnaces | Song Alchemy with the setlist's songs, or its Journey prompt from the opener to the closer. |

From any song in Navidrome, **Instant Mix** gives you a quick radio built on that song's sound, so for most single-artist lists you can skip making a playlist at all.

## 5. Concept recipes

Many of your playlists are the same idea saved several times: nine country pool playlists, eight Christian hip-hop workout ones, nine modern hymn ones. A recipe rolls each group into one prompt you can run whenever you want a fresh version. All 65 are in Playlist recipes.

**How they were built.**

- 326 of your 494 own mixes were grouped into 65 concepts by occasion, genre and era. The rest were one-offs that didn't fit a group, and they're covered by their own song-list prompts.
- **Seeds** are the songs that showed up in the most playlists within the group, with ties broken by how many playlists across your whole library had them. One song per artist; live versions, remixes and interludes skipped, and Christmas songs skipped outside the holiday recipes.
- **Artists named in the prompts** are the ones with the most songs across the group.
- **Eras** come from the middle 80% of release years in the group, so "2010s and 2020s" means most of the songs fell there.

**Trade-off.** A recipe averages a group, so the particular flavor of any one playlist gets lost. "Christian Car Bops for da nons" and "Today's Christian" share a recipe even though they probably feel different. If one specific playlist matters, use its own song-list prompt instead.

**Running a recipe.** Try the Instant Playlist prompt first. If it drifts, use the Song Alchemy seeds instead, which keeps it much closer to the original sound. For the best of both, run the prompt, then put two or three of its best results into Alchemy along with the seeds.

## 6. Clustering

Clustering groups your whole library by sound on its own schedule, and you don't control what comes out. It won't rebuild a specific playlist, but it's a good way to find groupings you'd never have made by hand.

- After a run, skim the cluster playlists for ones that look like an old playlist of yours, like a cluster full of Zac Brown Band and Kenny Chesney that's basically "Pool Tunes".
- If you want to keep one, save a copy under your own name. Every run deletes and replaces the playlists ending in `_automatic`, so the original won't last.
- A cluster that matches a recipe is a sign the recipe's sound is solid. A recipe with no matching cluster is usually one held together by lyrics or faith rather than sound.

## Faith music

AudioMuse can't tell Christian from secular music by sound. A Christian pop-punk song and a secular one land in the same place, so faith playlists need extra steering.

- **Name the artists.** Gemini knows which artists are Christian, so every faith prompt says "Christian artists only" and names Christian seed songs or artists. That's knowledge, not sound, so lesser-known artists can slip through either way.
- **Song Alchemy seeds** keep you close to the sound but can pull in secular bands that sound the same. Delete those after generating.
- **Save the clean run** (method 2). Once a faith playlist is trimmed and saved, it stays 100% faith, and Alchemy runs built on it start from the right place.

## Still unknown

- **How much of your Apple library is in Navidrome.** Seeds only work for songs you own. A seed you don't own is skipped and the rest of the prompt still runs, so a prompt with several missing seeds will drift. If that happens, swap in another song by the same artist.
- **Whether the prompts hold up.** They follow AudioMuse's limits as written in its code, but none has been run against your library yet. Try a few you know well first, like Pool Tunes or Youth Group Throwback, and judge from those.
