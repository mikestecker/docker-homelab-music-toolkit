# Playlist cover art: research trail

Design notes behind `app/modules/playlist_covers/`. The README documents how to use and
configure the feature; this file documents *why* it's built the way it is, for whoever
revisits it later.

## Reference repos (user-ranked, before this module was built)

Reviewed, in the user's stated preference order — the first two explicitly liked for style:

1. `sswanyuu/playlist-cover-generator` — Leonardo.AI backend, explicitly instructs the model
   to produce zero text in the image.
2. `mstrlc/playlist-cover-generator` — never asks an AI for text at all; overlays a real font
   on a generated/background image. (Uses a non-free font, "Humane" — not reusable here;
   we bundle OFL Google Fonts instead.)
3-8. The remaining six: a marketing landing page, an empty Vite scaffold, an unfinished
   personal script, a Google-Apps-Script project, and `davidsneighbour/posterboy-image-generator`
   (a genuinely reusable MIT-licensed layered-canvas editor — noted as a plausible v2 manual
   editor, not needed for v1's layout/font/style pickers).
9. `ai-music-channel-playbook` — a toolkit-shaped repo with a documented prompting lesson:
   image models produce garbled pseudo-lettering, so generate a clean plate and add lettering
   as a separate layer afterward. Its `tools/track-picker/` (audio defect screening, loudness
   normalization) is unrelated to cover art but flagged as a candidate future "library health"
   module, separate from this feature.

**Design principle, confirmed by #1, #2, and #9 independently**: never let an image model
render the title text. Every mode in this module composites the title as a real font layer
*after* generation, never as part of the image-gen prompt. `app/modules/playlist_covers/
service.py`'s `NO_TEXT_INSTRUCTION` constant is the enforcement point.

## Navidrome's real cover-art mechanism

Verified against Navidrome's actual Go source (not the stale 2020 GitHub issue thread, which
was the initial — incorrect — read). Two mechanisms ship today:

1. **Sidecar file** (`core/artwork/playlist_cover.go`, `findPlaylistSidecarPath`): an image
   with the same base filename (case-insensitive) as the `.m3u`/`.nsp` file, same folder.
   Auto-detected, no auth, no server config. Covers Tidarr imports and smart playlists —
   most of this library.
2. **Upload API** (`server/nativeapi/image_upload.go`, PR #5110, merged 2026-03-01; PR #5131,
   merged 2026-03-02): `POST`/`DELETE /api/playlist/{id}/image`, native bearer auth, gated by
   `checkImageUploadPermission` — needs `ND_USER` to be a Navidrome admin, or Navidrome's own
   `EnableArtworkUpload` config set. The only path for playlists with no backing file.

An earlier, unmerged PR (#3727, filename-matching approach) was superseded by the above and is
not what's implemented.

## Replicate / Imagen-4

Initially built against a generic Stable-Diffusion-style schema (version-hash `/v1/predictions`,
`width`/`height`/`negative_prompt` fields) — wrong assumption. The user's actual Replicate
account defaults to `google/imagen-4`, called via the *official-model* endpoint
(`POST /v1/models/{owner}/{name}/predictions`, no version hash, always latest). Verified the
real input schema live via the API before the demo token expired: `prompt`, `image_size`
(default "1K"), `aspect_ratio` (default "1:1"), `output_format`, `safety_filter_level` — no
`negative_prompt` field, so the "no text" instruction is folded into the positive prompt.

Pricing (self-reported by the user from https://replicate.com/pricing, not independently
re-verified since): `google/imagen-4` ~$0.04/image, `google/imagen-4-fast` ~$0.02/image,
`black-forest-labs/flux-dev` ~$0.025/image. `.env.example` defaults to `imagen-4`; `-fast` is
noted as a cheaper "good enough" alternative. Replicate's own pricing page is the source of
truth if this drifts.

### Medium article: "A Practical Guide to Google's Imagen 4" (charmichokshi)

User-pasted in full (WebFetch couldn't reach it directly). Relevant takeaways actually used:

- SCULPT framework / 8-part prompt structure (style, theme/mood, scene, atmosphere,
  composition, palette, negative list, format) — basis for `build_prompt()`'s structure.
- Explicit confirmation of the no-baked-text lesson: *"for pixel-perfect fonts and layout,
  you'll still get the cleanest results by adding text later in your design tool."* This is
  what settled the one disagreement with Gemini's advice below.
- Composition guidance on reserving a title-safe zone informed `_LAYOUT_COMPOSITION_HINTS`.

### Gemini prompt advice (user-pasted)

Useful part adopted: richer, more scene-grounded prompt phrasing per vibe (lo-fi, workout,
indie rock, synthwave) — folded into `STYLE_PRESETS`.

Part explicitly rejected: Gemini suggested letting Imagen 4 render the title directly
("Bold minimalist sans-serif text... reading '[Your Title]'"). Disagreed for three concrete
reasons, independently confirmed by the Medium article above:
1. Renaming a playlist would require a paid regeneration instead of a free re-composite.
2. It breaks the 6-layout compositing system, which assumes the background has no text yet.
3. It contradicts the playbook repo's own documented lesson (see above).

## Competitor/landscape scan (2026-10-11, post-build)

12 pages fetched and reviewed (3 YouTube links in the original list were skipped — WebFetch
converts pages to text and can't watch video; a screenshot or transcript would be needed to
get anything from those).

- **Spotify's own "Create Cover Art"** (newsroom posts, Oct 2024 + Jun 2025) is *manual*, not
  AI-generated: upload a photo, add text/gradients/stickers, one cover per playlist (overwrites
  on edit). This module already automates more than Spotify's native tool does.
- **Consistent legibility guidance** across RouteNote, SoundCamps, Kapwing: 3-4 words max,
  bold sans-serif, avoid thin/script fonts, square format, central focal point with reserved
  text space. Validates the layout/font defaults already chosen; the two script fonts (Caveat,
  Pacifico) are the deliberate exceptions, opt-in rather than default.
- **Genre-flavored presets** (PhotoCut: rock/jazz/hip-hop/soul; AlbumCover.art: Hip-Hop/EDM/Indie)
  — largely already covered by this module's mood-based presets (synthwave, lofi, indie-film,
  neon-energy) rather than genre-named ones.
- **Coverify** uses curated real photography (Unsplash) instead of generation — validates the
  Picsum-sourced `photo-*` backgrounds already built for template mode.
- Two ideas surfaced that aren't in the current build, reviewed with the user and **deferred**
  (see README's "What's deliberately not built yet"):
  1. **Style locking** (AlbumCover.art) — a default style/layout/font so a whole library's
     playlists look cohesive, instead of choosing per playlist every time.
  2. **Iterative refinement** (Blend/DesignGPT's "Assist") — a free-text tweak field appended
     to the prompt for a quick regenerate, instead of only discrete dropdowns.

## Known open item

No valid (non-expired) Replicate token was available during this build. AI mode is built and
unit-tested against a fake Replicate mock (`tests/mocks/mock_replicate.py`), but has never been
exercised end-to-end against the real Imagen-4 service. Re-verify once a real token is set.
