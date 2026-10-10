# Occasion Library Playlist Playbook

135+ playlist recipes built from the **occasion-library ledger** — the 8,539-album wantlist merged from three AI platforms' "must-have albums" research (`expanded-data/`, deduplicated by `scripts/import_occasion_library.py` into `output/occasion-library.json`). This replaces the earlier *Playlist Playbook* built from Claude's 6,508-album CSV alone: same AudioMuse-AI workflow, but pulling from the full merged catalog, its richer per-album `genres`/`tags` fields, and the Skip list already set inside the app.

**This is a forward-looking plan, not a today list.** As of this writing the occasion-library albums haven't been downloaded yet — they're still sitting in the Occasion Library's Wanted queue, waiting on Navidrome matching and Tidarr requests. Treat everything below as the playlist game plan for once the vault fills in, not something to run against AudioMuse this afternoon. Re-check a recipe's seed albums are actually on disk before you build it.

## What changed from the old playbook

- **Source**: the old doc read a single flat CSV with one `Genre` column. This one reads the occasion-library ledger's two array fields per album — `genres` (one or more genre labels, inherited from whichever of the three platforms had the richest data for that album) and `tags` (editorial occasion/mood/vibe labels — "Pool party," "Workout," "Date night," and so on). Filter by either field in the Occasion Library screen's search box (it matches album, artist, genre, *and* tag text) or directly in `output/occasion-library.json`.
- **Scale**: 8,539 albums after merging and deduplicating ChatGPT's, Claude's, and Grok's lists (up from 6,508), with much deeper coverage in metal, jazz, ambient/classical, film scores, and Latin — see the new deep-dive sections below that the old doc didn't have room for.
- **The Skip list is already applied.** 79 albums are marked Skip in the occasion ledger (Bethel Music, CeCe Winans solo and both BeBe & CeCe castings, Elevation Worship and its Maverick City collab, Hillsong Worship, Fred Hammond, Gaither Vocal Band, Jesus Culture, Kim Walker-Smith, Point of Grace, Vertical Worship, Yolanda Adams, Bill & Gloria Gaither, The Winans). None of those artists appear as seeds anywhere below. Hillsong United, Hillsong UNITED, and Hillsong Young & Free were deliberately kept and still show up in the Faith section.
- Good recipes from the old doc are carried over where the artist and album are confirmed present in this catalog; recipes that leaned on albums or artists not in the merged library were dropped or re-seeded against what's actually here.

## How to build them

Two tools get you most of the way: the library's genre/tag data narrows *what* goes in, and AudioMuse's sonic analysis decides *how it feels*. Mix them and the playlists stay on-theme without sounding random.

| AudioMuse feature | Best for | How to use it here |
| --- | --- | --- |
| Instant Playlist | Most recipes below | Paste the "AudioMuse prompt" column. Add a genre word to keep it on-theme, like "upbeat 2000s pop country for a pool party." |
| Similar Songs | Tight, consistent vibes | Pick one seed track from the seed list and let it find the sonic neighbors. |
| Song Path | Playlists that build or wind down | Start on a calm track and end on a peak track (or the reverse). Great for workouts, parties, and bedtime. |
| Song Alchemy | Removing what doesn't fit | ADD a few seeds, SUBTRACT the outliers (e.g., subtract metal from a workout mix for pickleball). |
| Text Search | Mood plus instrument | "Calm piano," "acoustic guitar with female vocals," "brass and horns." |
| Lyrics Search | Themes | "Summer," "ocean," "road," "grace," "Friday night." Great for themed lists. |
| Clustering + Music Map | Discovering new combos | Run it after everything is analyzed and name the clusters that look useful. |
| Sonic Fingerprint | Your everyday mix | Builds from what you actually play most, once you have some listening history. |

A few rules that keep playlists sounding good:

- **Keep it 2 to 4 hours for events** (40 to 70 songs). Long enough to never repeat, short enough to stay focused.
- **Cap each artist at 2 to 3 songs** so one big discography doesn't take over.
- **For guests, use the clean versions where it matters.** A chunk of this library's hip-hop, pop, and rock albums carry an "explicit" tag in the raw research; keep an eye on it for daytime/mixed-age lists.
- **Filter by genre or tag in the occasion-library data first** when a recipe says "Pull from." The Occasion Library screen's search box matches genre and tag text directly — no spreadsheet needed.

## How this library's data actually works

Every album in `output/occasion-library.json` carries:

- **`genres`** — one or more genre labels. The vocabulary is a genuine three-way blend (ChatGPT's "Listening category"/"Original genre group," Claude's free-text "Genre," Grok's "genre"), so the same idea shows up at different granularities — "Classic Rock," "classic rock," and "Rock and Alternative" are all real, distinct values in the data, not a bug. Search loosely (substring, not exact match) the way the recipes below do.
- **`tags`** — editorial occasion/mood/vibe labels, unioned across every platform that tagged that album. The two biggest families are **situational** (ChatGPT's capitalized "Pool party," "Road trip," "Yard work," "Workout," "Pickleball," "Game night," "Dinner," "Date night," "Christian listening," "Reflection," "Study," "Worship" — and Grok's lowercase `pool`/`dinner`/`work`/`cook`/`yard`/`garage`/`game`/`workout`/`road`/`chores`) and **intimacy/adult-mood** (from "Modern R&B / date-night selection" and "Slow romantic / quiet storm selection" down through increasingly specific labels like "Sexual / provocative pop" or "Dark / seductive rock" — these are broad editorial lanes, not a claim about any specific lyric).
- **`deliberateNonstandard`** — true for the ~83 albums a source platform explicitly reviewed and chose a deluxe/expanded edition for on purpose (Halestorm's self-titled deluxe, Lords of Acid's *Voodoo-U*, and the like). Everything else in this library resolves to the artist's standard release when it's actually requested, by design (see `CLAUDE.md`).
- **`tidalIdHints`** — unverified Tidal album IDs carried over from the source CSVs. Never trust these for playlist-building; they're there for the app's own re-matching, not for you.

## Parties and get-togethers

For mixed crowds, go for songs everyone half-knows and keep the energy steady.

| Playlist | Pull from | Seed albums / artists | AudioMuse prompt | Notes |
| --- | --- | --- | --- | --- |
| **Pool Party (all ages)** | tags: Pool party, Dancing; genres: Pop, Upbeat Pop / Dance Party, Reggae / Island / Beach | Ace of Base *The Bridge*, Sublime, Bruno Mars, Jason Mraz, Dua Lipa, Kenny Chesney | "sunny upbeat party songs, danceable, happy, summer" | 3 to 4 hours. Song Path from Jack Johnson into something louder for a slow build through the afternoon. |
| **Adults-Only Pool Party** | tags: Pool party, Sensual / sexually themed, Sexual / provocative pop; genres: Dirty / Sexy Pop & Dance, Latin | Bad Bunny *Debí Tirar Más Fotos*, Doja Cat *Hot Pink*, Megan Thee Stallion, Tove Lo, Britney *Blackout* | "hot summer party, reggaeton and hip hop, high energy, danceable" | Explicit OK. Peaks around 5 to 8pm. |
| **Pool Lounge (laid-back)** | tags: Pool lounge; genres: Jazz and Instrumental, Ambient Classical and Focus, R&B and Intimacy | ACOUSTIC ALCHEMY, Al Di Meola *Elegant Gypsy*, A Winged Victory For The Sullen, 6LACK, Aaliyah | "laid-back instrumental and smooth R&B, relaxed, sunny, mellow groove" | Lower energy than the party list. Good for floats and drinks. |
| **Backyard BBQ** | genres: Classic Rock, Country, R&B / Soul / Funk / Disco | CCR, Tom Petty, Zac Brown Band, Earth Wind & Fire, Jimmy Buffett | "feel-good classic rock and country, sing-along, warm, mid-tempo" | Crosses generations. |
| **Game Night** | genres: Pop, 90s Rock / Alternative, 2000s+ Alternative / Indie, Britpop / UK Rock; tags: Game night | Blur, Vampire Weekend, The Killers *Hot Fuss*, Weezer, Del Amitri | "fun upbeat indie and alt rock, playful, medium energy, not too loud" | Keep it mid-volume so conversation and rounds hold together. |
| **Kitchen Dance Party** | genres: R&B / Soul / Funk / Disco, Dance / Electronic, Pop | Cameo *Word Up*, Bee Gees, Anderson .Paak *Malibu*, Bruno Mars | "disco and funk, very danceable, groovy, 115 to 125 bpm" | Song Path from Earth Wind & Fire into straight-up dance/electronic. |
| **Living Room Dance Floor** | genres: Dance / Electronic, Upbeat Pop / Dance Party, Latin | Above & Beyond *Group Therapy*, Alesso *Forever*, Afrojack, Alok | "high energy dance floor, club bangers, euphoric, 124 to 130 bpm" | Late-night peak. Keep ballads on a separate list for the cooldown. |
| **Sing-Along Anthems** | genres: Classic Rock, 80s Hard Rock / Hair Metal, 90s Rock / Alternative | Bon Jovi *Forever*, Europe *The Final Countdown*, Def Leppard, Extreme | Lyrics Search "anthem chorus" or Instant Playlist "huge sing-along choruses everyone knows" | For the end of the night. |
| **80s Night** | genres: 80s Hard Rock / Hair Metal; tags matching 1980s releases | Cinderella *Heartbreak Station*, Billy Squier, Damn Yankees, Europe, Firehouse | "1980s synth pop and arena rock, upbeat, nostalgic" | Pair with "New Wave" genre rows (Blondie, Talking Heads, The Cars, The Police) for the synthier half of the decade. |
| **90s Night** | genres: 90s Rock / Alternative, Pop | Alanis Morissette, Blur, Crash Test Dummies, Cake, 10,000 Maniacs | "90s alternative and pop hits, upbeat, nostalgic" | Mix eras inside the decade so it isn't all one sound. |
| **Grunge Only** | genre: grunge (small in this library — pair with 90s Rock / Alternative to round it out) | L7 *Bricks Are Heavy*, plus Alice In Chains, Soundgarden, Stone Temple Pilots from 90s Rock / Alternative | "Seattle grunge, heavy and moody, sludgy guitars" | This library's dedicated `grunge` tag is thin — most of the real grunge weight lives under 90s Rock / Alternative instead. |
| **Friendsgiving / Dinner Party** | tags: Dinner; genres: Jazz and Instrumental, R&B and Intimacy | Air *Moon Safari*, Bill Evans, ACOUSTIC ALCHEMY, Corinne Bailey Rae | "warm acoustic jazz and soul, relaxed dinner background, low volume" | Background that doesn't fight conversation. |
| **Karaoke Warm-Up** | genres: Pop, Classic Rock, Country | ABBA, Alabama *40 Hour Week*, Alan Jackson, AC/DC | Lyrics Search across the classics, or "famous singable pop songs" | Pair with a TV lyrics app. |

## Active

For workouts, tempo matters more than genre. Song Path is ideal here because it ramps up and back down for you.

| Playlist | Pull from | Seed albums / artists | AudioMuse prompt | Notes |
| --- | --- | --- | --- | --- |
| **Heavy Lifting** | genres: Metal / Heavy Rock (Workout), Heavy Rock and Metal; tags: Workout | Amon Amarth *Berserker*, Anthrax *Among The Living*, Arch Enemy *Doomsday Machine*, All That Remains | "aggressive heavy metal, loud, intense, powerful riffs" | See the Heavy / Metal deep dive below — this library has real depth here (700+ metal-tagged albums). |
| **Arena Rock Pump-Up** | genres: Hard Rock / Metal, Modern Hard Rock, Classic Rock | Accept *Balls To The Wall*, Alter Bridge *AB III*, AC/DC *Back In Black* | "high energy hard rock, driving drums, motivational" | Less extreme than Heavy Lifting. |
| **Cardio / HIIT** | genres: Dance / Electronic, Hip Hop / Party Crowd Pleasers | Above & Beyond, Afrojack, Alok, Alesso | "very high energy, 128 to 140 bpm, intense build-ups and drops" | Use Alchemy to SUBTRACT anything under about 120 bpm. |
| **Running Pace** | genres: Pop Punk / Emo, 2000s+ Alternative / Indie; tags: Workout | blink-182, Fall Out Boy *American Beauty/American Psycho*, Jimmy Eat World, Dashboard Confessional | "steady upbeat 160 to 175 bpm running music" | Pop punk often sits right at a running cadence. |
| **Pickleball** | tags: Pickleball (1,661 albums tagged — huge, flexible pool); genres: Pop, Classic Rock, 2000s Rock | *NSYNC*, a-ha, 5 Seconds of Summer, Addison Rae, AC/DC | "fun upbeat energetic pop and rock, positive, bouncy, not aggressive" | This tag is broad by design — narrow it with a genre filter first, then Alchemy out anything too heavy. |
| **Yard Work** | tags: Yard work (2,706 albums — the single biggest occasion tag after "Usually vocal"); genres: Classic Rock, Country | .38 Special, Lynyrd Skynyrd, ZZ Top, Brooks & Dunn | "steady mid-tempo rock and country, upbeat, outdoorsy" | 3+ hours. Narrow by genre before building — the tag alone covers almost a third of the library. |
| **Garage / Project Day** | tags: garage; genres: Classic Rock, Hard Rock / Metal, Blues / Blues Rock | Bonnie Raitt, Buddy Guy, Gary Clark Jr., Joe Bonamassa | "gritty blues rock and classic rock, guitar driven" | Long album-style flow is fine here. |
| **House Cleaning Blitz** | tags: chores, Dancing; genres: Pop, R&B / Soul / Funk / Disco | Bell Biv DeVoe, Bobby Brown, Billy Ocean | "happy energetic pop and funk, motivating, sing-along" | 60 to 90 minutes is the sweet spot. |
| **Cool-Down Stretch** | genres: Ambient / Neo-Classical / Piano, Chill / Downtempo / Lo-Fi | A Winged Victory For The Sullen, Boards of Canada *The Campfire Headphase*, Bonobo *Black Sands* | "slow calm ambient, relaxed, gentle" | Song Path it onto the end of any workout list. |

## On the road

A road trip list should feel like a story: start bright, settle in, sing loud, then wind down as the sun sets.

| Playlist | Pull from | Seed albums / artists | AudioMuse prompt | Notes |
| --- | --- | --- | --- | --- |
| **Family Road Trip** | tags: Road trip (2,967 albums, the second-biggest tag); genres: Pop, Pop Country, Classic Rock | ABBA, Alan Jackson, America | "upbeat sing-along road trip songs, happy, family friendly" | Clean versions. 5+ hours so nobody hears repeats. |
| **Highway Classic Rock** | genres: Classic Rock | Ambrosia *Life Beyond L.A.*, Bad Company, Bachman-Turner Overdrive | "open road classic rock, driving rhythm, nostalgic" | The default long-haul pick — this is the single biggest genre in the library (1,068 albums). |
| **Country Highway** | genres: Country, Pop Country, country | Alan Jackson *34 Number Ones*, Alison Krauss, Ashley McBryde | Lyrics Search "truck road highway" or "country driving songs, mid-tempo" | Country (and its "country"/"country pop" variants) is the third-biggest genre in the library at nearly 1,400 albums combined. |
| **Desert Night Drive** | genres: Sultry / Trip-Hop / Dark Pop, Dance / Electronic | Chromatics *Kill for Love*, BANKS *The Altar*, Beach House *Bloom*, Cigarettes After Sex | "moody nighttime driving, synthwave and dark pop, steady pulse" | For coming home late. |
| **PCH Coast Cruise** | genres: Reggae / Island / Beach, Yacht Rock / Smooth | Big Mountain, Ben Harper, Al Jarreau *Breakin' Away*, Christopher Cross | "sunny coastal drive, breezy, warm, windows-down" | Pair with a drive to the coast. |
| **Mountain Drive** | genres: Acoustic / Singer-Songwriter, Folk / Americana / Jam | Boy Pablo, Briston Maroney, Hippo Campus, Easy Life | "folk and indie, warm acoustic, open and scenic" | Good for the climb and the cabin both. |
| **Commute Wake-Up** | genres: 2000s+ Alternative / Indie, Modern Hard Rock | Beach Bunny, Boy Pablo, Dayglow | "energetic alt rock, motivating morning" | 30 to 45 minutes. |
| **Commute Wind-Down** | genres: Yacht Rock / Smooth, R&B and Intimacy | Bob James *Touchdown*, Chuck Mangione, Atlantic Starr | "relaxed smooth evening drive, mellow, soulful" | Leaves work at work. |

## Focus and quiet

Words pull your attention, so focus lists lean instrumental. This is where the merged library is genuinely deeper than the old doc — jazz, ambient/neo-classical, classical, and film/game scores all have real weight here.

| Playlist | Pull from | Seed albums / artists | AudioMuse prompt | Notes |
| --- | --- | --- | --- | --- |
| **Deep Work (no vocals)** | genres: Ambient Classical and Focus, Ambient / Neo-Classical / Piano, Film & Game Scores | A Winged Victory For The Sullen, Boards of Canada, C418 *Minecraft - Volume Alpha*, Clint Mansell *Moon* | "instrumental focus music, steady, no vocals, low distraction" | 3+ hours on loop. See the dedicated deep dives below. |
| **Lo-Fi Workday** | genres: Jazz and Instrumental, Chill / Downtempo / Lo-Fi | Badbadnotgood *III*, Baby Rose *Slow Burn*, Alfa Mist *Antiphon* | "lo-fi hip hop beats, mellow jazz chords, chill" | Light vocals are fine here. |
| **Coffee Shop Jazz** | genre: Jazz | Ahmad Jamal, Art Blakey & The Jazz Messengers *Moanin'*, Bill Evans Trio, Billie Holiday *Lady in Satin* | "relaxed acoustic jazz, piano and saxophone, morning coffee" | Good for slow weekend mornings too. |
| **Study Hall** | genres: Classical, Ambient Classical and Focus | András Schiff *Bach: Goldberg Variations*, Alice Sara Ott, Arthur Rubinstein, Academy of St Martin in the Fields | "calm classical piano and strings, concentration" | Deep, real classical coverage — see the deep dive below. |
| **Creative Flow** | genres: Film & Game Scores, Dance / Electronic | Daft Punk *TRON: Legacy Reconfigured*, Darren Korb *Hades*, Austin Wintory *Journey* | "cinematic, building, inspiring electronic" | Steady pulse, a little drama. |
| **Quiet Time / Reading** | genres: Acoustic / Singer-Songwriter, Folk / Americana / Jam; tags: Quiet time | Boy Pablo, Cuco *Para Mí*, Briston Maroney | "soft acoustic, gentle vocals, intimate, calm" | Low volume, warm. |
| **Sleep / Wind Down** | genre: Ambient / Neo-Classical / Piano | A Winged Victory For The Sullen, Biosphere *Substrata + Man with a Movie Camera*, Boards of Canada | "very calm ambient, sleep, slow, soft, no drums" | Set a sleep timer. |
| **Meditation / Reflection** | tags: Reflection, Quiet time; genres: Ambient Classical and Focus, Christian Reflective / Hymns | A Winged Victory For The Sullen, plus the Faith section's Prayer and Reflection picks | "peaceful, spacious, slow, meditative" | Pairs with the Faith section below. |

## Faith

Tagged by mood (Christian Pop / CCM, Christian Worship / Worship, Christian Rock / Alternative, Christian Hip-Hop, Christian Gospel, Christian Reflective / Hymns) with a "Christian listening" tag running across all of them. **Every seed below was checked against the current Skip list** — Bethel Music, CeCe Winans, BeBe & CeCe Winans (both castings), Elevation Worship (solo and the Maverick City collab), Hillsong Worship, Fred Hammond, Gaither Vocal Band, Jesus Culture, Kim Walker-Smith, Point of Grace, Vertical Worship, Yolanda Adams, Bill & Gloria Gaither, and The Winans are skipped and don't appear here. Hillsong United stays.

| Playlist | Pull from | Seed albums / artists | AudioMuse prompt | Notes |
| --- | --- | --- | --- | --- |
| **Sunday Drive (upbeat CCM)** | genre: Christian Pop / CCM | Amy Grant *Age To Age*, Audio Adrenaline *Bloom*, Avalon *A Maze of Grace*, Brandon Heath | "upbeat joyful Christian pop and rock, positive, energetic" | Family friendly by default. |
| **Sunday Worship** | genres: Christian Worship, Worship; tags: Worship | Brandon Lake *COAT OF MANY COLORS*, Chris Tomlin *Always*, Cory Asbury *Outsing The Angels*, Brooke Ligertwood *EIGHT*, Cody Carnes | "congregational worship, building, anthemic" | Song Path from a quiet opener up to an anthem. |
| **Prayer and Reflection** | genre: Christian Reflective / Hymns; tags: Reflection, Quiet time | Charlie Hall *The Bright Sadness*, Bethany Dillon *Imagination*, Benjamin William Hastings | "quiet reflective worship, soft piano and acoustic, prayerful" | Journaling, early mornings. |
| **Gospel Joy** | genre: Christian Gospel | Kirk Franklin *The Essential Kirk Franklin*, Donald Lawrence *Finale: Act II*, Hezekiah Walker, Israel & New Breed, Andraé Crouch | "joyful gospel choir, uplifting, clapping" | Saturday cleaning or a backyard brunch. |
| **Faith Workout** | genre: Christian Hip-Hop; cross with Metal / Heavy Rock (Workout) for intensity | Lecrae *All Things Work Together*, Andy Mineo *I: The Arrow*, KB *His Glory Alone*, Trip Lee, Tedashii | "high energy Christian rock and hip hop, intense, motivating" | Christian Hip-Hop is a real, if smaller, lane here — about two dozen albums. |
| **Worship Night In** | genre: Christian Worship; tags: Worship, Quiet time | Hillsong United, Cody Carnes *Firm Foundation (Live)*, All Sons & Daughters | "spontaneous live worship, long and spacious, intimate" | Longer songs, fewer transitions. |
| **Christian Rock Radio** | genre: Christian Rock / Alternative | Pull titles tagged Christian Rock / Alternative directly from the ledger — this lane is smaller post-Skip, so check what's actually present before seeding | "big guitars, big choruses, Christian rock radio" | Verify seeds in-app; several familiar 2000s CCM-rock names from the old doc aren't confirmed in this merged catalog yet. |

## Date night and bedroom

These go from dinner-table romantic to the library's "Dirty / Sexy" and "Adult mood" tags. Build these with Song Path so the energy rises or falls on purpose, and keep them off the pool-party shuffle.

| Playlist | Pull from | Seed albums / artists | AudioMuse prompt | Notes |
| --- | --- | --- | --- | --- |
| **Romantic Dinner** | tags: Dinner, Date night; genres: Jazz and Instrumental | Billie Holiday *Lady in Satin*, Bill Evans, Ahmad Jamal | "romantic candlelit dinner jazz, soft vocals, warm" | Low volume. ~90 minutes. |
| **Slow and Sensual** | tags: Slow romantic / quiet storm selection; genre: Slow Jams / Quiet Storm | Al Green *Greatest Hits*, Anita Baker *The Best of Anita Baker*, Atlantic Starr, Babyface | "slow romantic soul and quiet storm, sensual, smooth, 60 to 80 bpm" | 216 albums carry this genre tag — plenty of range. |
| **Modern Late Night R&B** | tags: Modern R&B / date-night selection; genre: Slow Jams / Quiet Storm | 6LACK *East Atlanta Love Letter*, Ari Lennox, Alina Baraz, Ashanti | "moody sensual modern R&B, late night, atmospheric" | Steamier than the classics. Explicit versions. |
| **Sensual / Explicit** | tags: Sensual / sexually themed selection | Adina Howard *Do You Wanna Ride?*, Jodeci, Ginuwine *100% Ginuwine*, Marvin Gaye *I Want You*, Janet Jackson *20 Y.O.* | "sexy, sultry, explicit R&B, slow grind" | This tag exists specifically so lists like this one are easy to find and keep separate from the family lists. |
| **Dark and Sultry** | genre: Sultry / Trip-Hop / Dark Pop; tags: Dark / seductive rock | BANKS *The Altar*, Chromatics *Kill for Love*, The Faint, Cigarettes After Sex, She Wants Revenge | "dark sensual trip hop, slow, hypnotic, breathy vocals" | Candlelight and a slow pulse. |
| **Dirty Rock** | genre: Dirty / Sexy Rock | Meg Myers, Garbage *Beautiful Garbage*, The Kills *Blood Pressures*, Two Feet | "sexy dirty rock, swagger, sultry vocals, driving" | The louder, more confident alternative to slow jams. |
| **Dirty Pop** | tags: Sexual / provocative pop, Provocative / dirty party pop | Britney *Blackout*, Christina Aguilera *Back To Basics*, Doja Cat *Hot Pink*, Madonna *Bedtime Stories*, Tove Lo | "sexy confident pop, flirty, danceable" | Getting-ready music too. |

## Themed and seasonal

| Playlist | Pull from | Seed albums / artists | AudioMuse prompt | Notes |
| --- | --- | --- | --- | --- |
| **Yacht Rock Happy Hour** | genre: Yacht Rock / Smooth | Al Jarreau, Al Stewart *Year of the Cat*, Ambrosia *Anthology*, Christopher Cross, Bob James, Captain & Tennille | "smooth 70s soft rock, breezy, sophisticated, mellow" | Five o'clock on the patio. |
| **Tailgate / Game Day** | genres: Country, Pop Country, Classic Rock, Hip Hop / Party Crowd Pleasers | Alan Jackson, AC/DC, mix in Hip Hop / Party genre rows for variety | "rowdy party country and stadium rock, high energy" | Clean versions in public. |
| **Latin Night** | genre: Latin (153 albums, plus 37 Latin Pop and 33 latin pop variants — ~220 total) | Bad Bunny *Debí Tirar Más Fotos*, Aventura *God's Project*, Café Tacvba, Buena Vista Social Club, Banda MS, Alejandro Fernández | "festive latin party, cumbia salsa and reggaeton, danceable" | See the Latin deep dive below. Split into a classic set and a modern reggaeton/corridos set. |
| **Oldies / Early Rock & Roll** | genre: Oldies / Early Rock & Roll | Chuck Berry *The Great Twenty-Eight*, Little Richard, Buddy Holly, Fats Domino, Ben E. King | Lyrics Search "sock hop diner" or "50s rock and roll, upbeat" | 30 albums. Great for a themed decades party. |
| **Halloween Party** | genre: Sultry / Trip-Hop / Dark Pop, Heavy Rock and Metal | Chromatics, The Faint, plus metal-genre rows for intensity | Lyrics Search "night ghost devil monster" | Season-appropriate, costume-party ready. |
| **Decades Journey** | Everything — one anchor album per decade | Oldies / Early Rock & Roll → Classic Rock → 80s Hard Rock / Hair Metal → 90s Rock / Alternative → 2000s+ Alternative / Indie → today's pop/hip-hop rows | Song Path chained decade to decade | A great party conversation piece, showing off the whole library. |
| **Reggae / Island Day** | genre: Reggae / Island / Beach (124 albums) | Bob Marley & The Wailers, Black Uhuru *Red*, Burning Spear *Marcus Garvey*, Big Mountain, Ben Harper | "laid-back reggae and surf rock, relaxed, sunny, mellow groove" | Pairs with Pool Lounge above. |

## Heavy / Metal deep dive

This is the single biggest expansion over the old doc — 402 albums tagged Heavy Rock and Metal, 324 tagged Metal / Heavy Rock (Workout), plus Hard Rock / Metal and Modern Hard Rock on top. Worth its own section rather than one row in a workout table.

| Playlist | Pull from | Seed albums / artists | AudioMuse prompt | Notes |
| --- | --- | --- | --- | --- |
| **Classic Metal** | genre: Heavy Rock and Metal | Accept *Balls To The Wall*, Dio *Holy Diver*, Anthrax *Among The Living*, Alice In Chains | "classic heavy metal, loud, powerful, iconic riffs" | The foundational set. |
| **Modern Metal / Metalcore** | genre: Metal / Heavy Rock (Workout) | Amon Amarth *Berserker*, Arch Enemy *Doomsday Machine*, All That Remains *The Fall Of Ideals*, Alter Bridge | "modern metal and metalcore, heavy, aggressive, melodic choruses" | This is the "Heavy Lifting" workout pool. |
| **Hard Rock Radio** | genre: Hard Rock / Metal, Modern Hard Rock | AC/DC *Back In Black*, Airbourne *Black Dog Barking*, Alter Bridge | "driving hard rock, big riffs, radio-ready" | Less extreme, good for a shared space. |
| **Industrial / Dark Metal** | tags: Sexual / provocative industrial metal, Dark / provocative metal | Cross-reference the Dark and Sultry date-night list above — the two genuinely overlap in this library's tagging | "dark industrial metal, heavy, moody, aggressive" | Small but real lane; check current tag counts before committing to a full playlist length. |

## Jazz & Instrumental deep dive

152 albums tagged Jazz and Instrumental, 73 more under a plain Jazz genre — genuine range from vocal standards to modern instrumental jazz-hop.

| Playlist | Pull from | Seed albums / artists | AudioMuse prompt | Notes |
| --- | --- | --- | --- | --- |
| **Jazz Standards** | genre: Jazz | Billie Holiday *Lady in Satin*, Ahmad Jamal, Bill Evans Trio *Sunday at the Village Vanguard*, Art Blakey & The Jazz Messengers | "classic vocal and piano jazz standards, warm, timeless" | The Romantic Dinner list's deeper well. |
| **Modern Instrumental Jazz** | genre: Jazz and Instrumental | Badbadnotgood *III*, Alfa Mist *Antiphon*, ACOUSTIC ALCHEMY | "modern instrumental jazz, groove-forward, contemporary" | Pairs well with Lo-Fi Workday above. |
| **Jazz Vocalists Night** | genre: Jazz; tags: Dinner | Billie Holiday, Baby Rose *Slow Burn* | "intimate jazz vocals, smoky, late night" | Low light, small room. |

## Film & Game Scores + Ambient/Classical deep dive

50 albums tagged Film Scores plus 49 more as Film & Game Scores, alongside 207 Ambient Classical and Focus and 100 Ambient / Neo-Classical / Piano albums, and 34 proper Classical records. This is real, substantial focus-music depth.

| Playlist | Pull from | Seed albums / artists | AudioMuse prompt | Notes |
| --- | --- | --- | --- | --- |
| **Movie Night Scores** | genres: Film Scores, Film & Game Scores | Alan Silvestri *Avengers: Endgame*, Alexandre Desplat *The Grand Budapest Hotel*, Ennio Morricone *Cinema Paradiso*, Clint Mansell *Moon* | "cinematic orchestral film score, sweeping, emotional" | Great for a slow Sunday or a writing session. |
| **Video Game Chill** | genre: Film & Game Scores | C418 *Minecraft - Volume Alpha*, ConcernedApe *Stardew Valley*, Darren Korb *Hades*, Austin Wintory *Journey*, Disasterpeace *Fez* | "cozy video game soundtracks for relaxed focus, gentle" | A whole lane of its own in this library — bigger than you'd expect. |
| **Solo Piano** | genre: Ambient / Neo-Classical / Piano | Alexis Ffrench *Evolution*, Alice Sara Ott, Alexandra Stréliski *INSCAPE* | "solo piano, gentle, introspective, minimal" | Studying, reading, or winding down. |
| **Baroque & Classical** | genre: Classical | András Schiff *Bach: Goldberg Variations*, Academy of St Martin in the Fields *Mozart*, Arthur Rubinstein *Chopin: Nocturnes* | "classical piano and chamber strings, elegant, focused" | Study Hall's deeper well. |
| **Ambient Drift** | genre: Ambient Classical and Focus | A Winged Victory For The Sullen, Biosphere, Boards of Canada *The Campfire Headphase*, Bonobo *Black Sands* | "ambient, textured, slow-building, no drums" | Sleep / Wind Down's deeper well. |

## Latin deep dive

~220 albums across Latin, Latin Pop, and latin pop — enough for a real multi-mood set, not just one party list.

| Playlist | Pull from | Seed albums / artists | AudioMuse prompt | Notes |
| --- | --- | --- | --- | --- |
| **Reggaeton & Trap Latino** | genre: Latin | Bad Bunny *Debí Tirar Más Fotos*, Becky G *Esquemas*, Camila *Todo Cambió* | "high energy reggaeton and Latin trap, danceable, confident" | The modern-party half of the deep dive. |
| **Regional Mexicano** | genre: Latin | Banda MS de Sergio Lizárraga, Carin León *Boca Chueca, Vol. 1*, Caifanes *El Silencio* | "regional Mexican, corridos and banda, festive" | Pairs with Sunday Carne Asada-style gatherings. |
| **Classic Latin / Bolero** | genre: Latin, Latin Pop | Alejandro Fernández *Confidencias*, Alejandro Sanz, Buena Vista Social Club | "classic Latin ballads and bolero, romantic, warm" | The dinner-party half. |

## Sources

- [AudioMuse-AI on GitHub](https://github.com/NeptuneHub/AudioMuse-AI): feature names (Instant Playlists, Similar Songs, Song Paths, Song Alchemy, Sonic Fingerprint, Music Map, Text and Lyrics Search, Clustering).
- Album, genre, and tag data: `output/occasion-library.json` (8,539 albums, merged and deduplicated from ChatGPT's, Claude's, and Grok's research under `expanded-data/` by `scripts/import_occasion_library.py`), cross-checked against the live Skip list via `GET /api/occasion/albums` as of this writing.
- Every seed album/artist named above was verified present in the active (non-skipped) occasion-library catalog at write time — none were invented. Counts cited (e.g., "402 albums tagged Heavy Rock and Metal") come from a direct tally of `output/occasion-library.json` and will drift as the Skip list, the catalog, or a future re-run of the ingest script changes it. Re-run the same tally before leaning hard on a specific number months from now.
