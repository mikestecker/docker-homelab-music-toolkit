"""Playlist cover art generation.

Two generation modes, one compositing rule that's never skipped: the playlist
title is always drawn as a real font layer after generation, never left to an
image model to render - see docs/playbook research in the plan this module
was built from. AI mode uses Replicate (Stable Diffusion); template mode
composites over a curated or user-supplied background. Both produce a
1024x1024 PNG, saved to history, and "apply" decides between Navidrome's two
real cover-art mechanisms:

  - sidecar file (same basename as the playlist's .m3u/.nsp, same folder) -
    the primary path, no Navidrome-side permission needed
  - POST /api/playlist/{id}/image - the fallback for playlists with no
    backing file, needs ND_USER to be a Navidrome admin or Navidrome's own
    EnableArtworkUpload setting
"""
import io
import os
import time
import uuid

from PIL import Image, ImageDraw, ImageFont

from app.core import config as cfg
from app.core import navidrome_client as nd
from app.core import replicate_client
from app.core import store
from app.core.navidrome_client import NavidromeError
from app.core.replicate_client import ReplicateError

SIZE = 1024
FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
BUILTIN_BACKGROUNDS_DIR = os.path.join(cfg.CONFIG_DEFAULTS_DIR, "cover-backgrounds")
PLAYLIST_FILE_EXTS = (".m3u", ".m3u8", ".nsp")

# Named style presets map to prompt fragments, not provider-specific style ids,
# so the list isn't tied to Replicate. Grounded in concrete scenes/objects
# rather than adjectives (the playbook's advice: "two or three concrete
# nouns beat any number of adjectives") - richer and more specific than a
# generic lighting descriptor, which is what actually drives good output
# from photoreal models like Imagen. "illustration" is the one deliberate
# non-photographic option, kept for variety.
STYLE_PRESETS = {
    "dynamic": ("a bold dynamic photograph, strong diagonal composition, high contrast "
               "lighting, sharp focus"),
    "cinematic": ("a cinematic film-still photograph, dramatic directional lighting, "
                 "shallow depth of field, moody atmosphere"),
    "bokeh": ("a photograph with soft dreamy bokeh, shallow depth of field, warm blurred "
             "highlights in the background"),
    "vibrant": "a vividly colored photograph, highly saturated, energetic and punchy",
    "illustration": "a flat illustrated artwork, clean shapes, modern poster style",
    "minimalist": "a minimalist photograph, clean composition, generous negative space",
    "lofi": ("a cozy minimalist room at night, a single warm desk lamp glowing on a stack "
            "of vinyl records and a steaming ceramic mug, rain trickling down a window "
            "with blurred city lights beyond, soft pastel color palette, dreamy atmosphere"),
    "neon-energy": ("an abstract composition of kinetic neon light trails in electric blue "
                    "and hot pink, dark matte textured background, high contrast, sharp focus"),
    "indie-film": ("an analog film photograph of an overgrown highway disappearing into a "
                   "hazy horizon under a pale orange sunset, visible grain, faded retro "
                   "1970s color grading, raw and melancholic mood"),
    "synthwave": ("a retro-futuristic scene on a wet reflective street at night under a "
                 "giant neon grid sun in purple and teal, cyberpunk aesthetic, crisp "
                 "volumetric lighting, high detail"),
}
DEFAULT_STYLE = "dynamic"

# The hard rule from the playbook: never let the model render text. Not
# every Replicate model has a separate negative_prompt input (Imagen and the
# Flux Pro family don't), so this is folded into the positive prompt text
# itself - which is what the playbook's own worked examples do too. The
# no-clutter clause matters for the same reason an album cover does: this
# renders as a small tile in a playlist list, not a full-screen image.
NO_TEXT_INSTRUCTION = ("Do not include any text, lettering, words, numbers, logos, "
                       "watermarks, signatures, or readable signage anywhere in the image. "
                       "No clutter - the composition should stay clear and readable at "
                       "small thumbnail size.")


def _custom_backgrounds_dir():
    return os.path.join(cfg.CONFIG_DIR, "cover-backgrounds")


def _covers_dir(playlist_id):
    return os.path.join(cfg.CONFIG_DIR, "covers", playlist_id)


def _manifest_path(playlist_id):
    return os.path.join(_covers_dir(playlist_id), "manifest.json")


def ai_available():
    return bool(cfg.REPLICATE_API_TOKEN and cfg.REPLICATE_MODEL)


def list_playlists():
    """Every playlist with enough info for the cover-art picker: name, id,
    and whether a sidecar cover file already sits next to its backing file
    (the only cover state this app can detect without extra Navidrome API
    surface - a cover set via the upload API looks the same as "unknown"
    here, which just means the UI shows "auto" rather than a wrong guess)."""
    try:
        playlists = nd.native_playlists()
    except NavidromeError as e:
        return {"playlists": [], "error": str(e)}
    out = []
    for p in playlists:
        local_path = _resolve_in_library(p["path"]) if p.get("path") else None
        has_sidecar = False
        if local_path and local_path.lower().endswith(PLAYLIST_FILE_EXTS):
            has_sidecar = os.path.isfile(os.path.splitext(local_path)[0] + ".png")
        out.append({"id": p["id"], "name": p["name"], "path": p.get("path"),
                    "file_backed": bool(local_path), "has_sidecar": has_sidecar})
    return {"playlists": out, "error": None}


def playlist_track_names(playlist_id, limit=20):
    try:
        entries = nd.get_playlist_entries(playlist_id, client="playlist-covers")
    except NavidromeError:
        return []
    names = []
    for e in entries[:limit]:
        title, artist = e.get("title"), e.get("artist")
        names.append(f"{title} by {artist}" if title and artist else (title or artist or ""))
    return [n for n in names if n]


STYLE_LABELS = {
    "dynamic": "Dynamic", "cinematic": "Cinematic", "bokeh": "Bokeh", "vibrant": "Vibrant",
    "illustration": "Illustration", "minimalist": "Minimalist", "lofi": "Lo-Fi",
    "neon-energy": "Neon Energy", "indie-film": "Indie Film", "synthwave": "Synthwave",
}


def list_styles():
    return [{"id": k, "label": STYLE_LABELS.get(k, k.capitalize()), "prompt": v}
            for k, v in STYLE_PRESETS.items()]


def list_backgrounds():
    out = []
    for source, directory in (("builtin", BUILTIN_BACKGROUNDS_DIR), ("custom", _custom_backgrounds_dir())):
        try:
            for name in sorted(os.listdir(directory)):
                if name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    out.append({"id": f"{source}:{name}", "source": source, "name": name})
        except OSError:
            continue
    return out


def _resolve_background_path(background_id):
    source, _, name = background_id.partition(":")
    directory = BUILTIN_BACKGROUNDS_DIR if source == "builtin" else _custom_backgrounds_dir()
    path = os.path.realpath(os.path.join(directory, name))
    root = os.path.realpath(directory)
    if os.path.commonpath([path, root]) != root:
        raise ValueError("invalid background id")
    if not os.path.isfile(path):
        raise ValueError(f"no such background: {background_id}")
    return path


def save_custom_background(filename, data):
    directory = _custom_backgrounds_dir()
    os.makedirs(directory, exist_ok=True)
    safe_name = os.path.basename(filename)
    if not safe_name or "/" in filename or "\\" in filename:
        raise ValueError("invalid filename")
    path = os.path.join(directory, safe_name)
    with open(path, "wb") as fh:
        fh.write(data)
    return f"custom:{safe_name}"


# ---------- fonts ----------
# Seven OFL-licensed Google Fonts spanning the vibes popular playlist covers
# draw on - licenses bundled in fonts/licenses/. Each layout below has a
# sensible default, but font and layout are independent choices.

FONTS = {
    "oswald":   {"label": "Oswald", "file": "Oswald-Variable.ttf", "bold_axis": [700],
                 "vibe": "bold condensed sans - modern, dynamic"},
    "anton":    {"label": "Anton", "file": "Anton.ttf", "bold_axis": None,
                 "vibe": "ultra-bold impact - loud poster type"},
    "bebas":    {"label": "Bebas Neue", "file": "BebasNeue.ttf", "bold_axis": None,
                 "vibe": "tall thin caps - minimal, editorial"},
    "playfair": {"label": "Playfair Display", "file": "PlayfairDisplay.ttf", "bold_axis": [700],
                 "vibe": "elegant serif - classy, editorial"},
    "caveat":   {"label": "Caveat", "file": "Caveat.ttf", "bold_axis": [700],
                 "vibe": "handwritten - personal, mixtape"},
    "mono":     {"label": "Space Mono", "file": "SpaceMono-Bold.ttf", "bold_axis": None,
                 "vibe": "monospace - lo-fi, retro-tech"},
    "pacifico": {"label": "Pacifico", "file": "Pacifico.ttf", "bold_axis": None,
                 "vibe": "retro script - vinyl, throwback"},
}
DEFAULT_FONT = "oswald"


def list_fonts():
    return [{"id": k, "label": v["label"], "vibe": v["vibe"]} for k, v in FONTS.items()]


def _font(font_id, size):
    meta = FONTS.get(font_id, FONTS[DEFAULT_FONT])
    font = ImageFont.truetype(os.path.join(FONTS_DIR, meta["file"]), size)
    if meta["bold_axis"]:
        try:
            font.set_variation_by_axes(meta["bold_axis"])
        except Exception:
            pass
    return font


# ---------- compositing ----------

def _fill_square(img):
    """Center-crop to a square, then resize to SIZE - matches the aspect
    Navidrome's own auto-tile uses (600x600; we generate a bit larger)."""
    w, h = img.size
    side = min(w, h)
    left, top = (w - side) // 2, (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    return img.resize((SIZE, SIZE), Image.LANCZOS)


def _fit_single_line(draw, text, font_id, max_width, start_size=110, min_size=28):
    size = start_size
    while size > min_size:
        font = _font(font_id, size)
        if draw.textlength(text, font=font) <= max_width:
            return font
        size -= 4
    return _font(font_id, min_size)


def _wrap_lines(draw, text, font, max_width):
    words = text.split()
    if not words:
        return [text]
    lines, cur = [], words[0]
    for w in words[1:]:
        trial = f"{cur} {w}"
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def _fit_multiline(draw, text, font_id, max_width, max_height, start_size=160, min_size=28, max_lines=3):
    size = start_size
    while size > min_size:
        font = _font(font_id, size)
        lines = _wrap_lines(draw, text, font, max_width)
        line_h = font.getbbox("Agjpy")[3] * 1.2
        block_h = line_h * len(lines)
        widest = max(draw.textlength(l, font=font) for l in lines)
        if len(lines) <= max_lines and block_h <= max_height and widest <= max_width:
            return font, lines, line_h
        size -= 6
    font = _font(font_id, min_size)
    lines = _wrap_lines(draw, text, font, max_width)[:max_lines]
    line_h = font.getbbox("Agjpy")[3] * 1.2
    return font, lines, line_h


def _shadow_text(draw, xy, text, font, fill=(255, 255, 255, 255), shadow=(0, 0, 0, 150), offset=3):
    x, y = xy
    draw.text((x + offset, y + offset), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill)


def _scrim_band(img, y0, y1, max_alpha=190, direction="down"):
    """Vertical gradient scrim over img[y0:y1], alpha ramping toward the
    band's outer edge so text always lands on the darkest part."""
    scrim = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(scrim)
    h = y1 - y0
    for i in range(h):
        t = i / h if direction == "down" else 1 - i / h
        draw.line([(0, y0 + i), (img.width, y0 + i)], fill=(0, 0, 0, int(max_alpha * t)))
    return Image.alpha_composite(img, scrim)


def _full_scrim(img, alpha=90):
    scrim = Image.new("RGBA", img.size, (0, 0, 0, alpha))
    return Image.alpha_composite(img, scrim)


# ---------- layouts ----------
# Each takes a SIZE x SIZE RGB image (already square-cropped by
# composite_title) and returns an RGBA image with the title composited.
# Six archetypes covering the popular playlist-cover treatments: a bottom
# scrim banner, an editorial top-left corner, a full-bleed poster title, a
# centered minimal badge, a side panel (the playbook's recommended
# composition), and a retro vinyl-label badge.

def _layout_bottom_banner(img, title, font_id):
    img = img.convert("RGBA")
    band_h = int(SIZE * 0.30)
    img = _scrim_band(img, SIZE - band_h, SIZE, max_alpha=195, direction="down")
    draw = ImageDraw.Draw(img)
    text = title.strip().upper()
    font = _fit_single_line(draw, text, font_id, SIZE * 0.86)
    w = draw.textlength(text, font=font)
    x, y = (SIZE - w) / 2, SIZE - band_h * 0.58
    _shadow_text(draw, (x, y), text, font)
    return img


def _layout_top_editorial(img, title, font_id):
    img = img.convert("RGBA")
    band_h = int(SIZE * 0.32)
    img = _scrim_band(img, 0, band_h, max_alpha=185, direction="up")
    draw = ImageDraw.Draw(img)
    margin = int(SIZE * 0.07)
    draw.line([(margin, margin + 30), (margin + 70, margin + 30)], fill=(255, 255, 255, 230), width=4)
    text = title.strip().upper()
    font, lines, line_h = _fit_multiline(draw, text, font_id, SIZE - margin * 2, band_h * 0.62,
                                          start_size=90, max_lines=2)
    y = margin + 46
    for line in lines:
        _shadow_text(draw, (margin, y), line, font)
        y += line_h
    return img


def _layout_big_bleed(img, title, font_id):
    img = img.convert("RGBA")
    img = _full_scrim(img, alpha=110)
    draw = ImageDraw.Draw(img)
    text = title.strip().upper()
    font, lines, line_h = _fit_multiline(draw, text, font_id, SIZE * 0.88, SIZE * 0.7,
                                          start_size=220, min_size=48, max_lines=3)
    block_h = line_h * len(lines)
    y = (SIZE - block_h) / 2
    for line in lines:
        w = draw.textlength(line, font=font)
        x = (SIZE - w) / 2
        _shadow_text(draw, (x, y), line, font, offset=4)
        y += line_h
    return img


def _layout_center_badge(img, title, font_id):
    img = img.convert("RGBA")
    draw = ImageDraw.Draw(img)
    text = title.strip().upper()
    pad_x, pad_y = 70, 44
    font, lines, line_h = _fit_multiline(draw, text, font_id, SIZE * 0.6, SIZE * 0.3,
                                          start_size=72, max_lines=2)
    block_h = line_h * len(lines)
    widest = max(draw.textlength(l, font=font) for l in lines)
    box_w, box_h = widest + pad_x * 2, block_h + pad_y * 2
    bx0, by0 = (SIZE - box_w) / 2, (SIZE - box_h) / 2
    badge = Image.new("RGBA", img.size, (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(badge)
    bdraw.rounded_rectangle([bx0, by0, bx0 + box_w, by0 + box_h], radius=22, fill=(0, 0, 0, 165))
    img = Image.alpha_composite(img, badge)
    draw = ImageDraw.Draw(img)
    y = by0 + pad_y
    for line in lines:
        w = draw.textlength(line, font=font)
        x = (SIZE - w) / 2
        _shadow_text(draw, (x, y), line, font)
        y += line_h
    return img


def _layout_sidebar(img, title, font_id, side="right"):
    img = img.convert("RGBA")
    band_w = int(SIZE * 0.42)
    x0 = SIZE - band_w if side == "right" else 0
    panel = Image.new("RGBA", img.size, (0, 0, 0, 0))
    pdraw = ImageDraw.Draw(panel)
    for i in range(band_w):
        t = i / band_w if side == "right" else 1 - i / band_w
        alpha = int(70 + 150 * t) if side == "right" else int(220 - 150 * t)
        x = x0 + i
        pdraw.line([(x, 0), (x, SIZE)], fill=(0, 0, 0, max(0, min(255, alpha))))
    img = Image.alpha_composite(img, panel)
    draw = ImageDraw.Draw(img)
    text = title.strip().upper()
    margin = int(band_w * 0.16)
    font, lines, line_h = _fit_multiline(draw, text, font_id, band_w - margin * 2, SIZE * 0.7,
                                          start_size=96, max_lines=6)
    block_h = line_h * len(lines)
    y = (SIZE - block_h) / 2
    tx = x0 + margin
    for line in lines:
        _shadow_text(draw, (tx, y), line, font)
        y += line_h
    return img


def _layout_vinyl_badge(img, title, font_id):
    img = img.convert("RGBA")
    img = _full_scrim(img, alpha=60)
    cx, cy, r = SIZE * 0.5, SIZE * 0.62, SIZE * 0.30
    disc = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ddraw = ImageDraw.Draw(disc)
    ddraw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(10, 10, 12, 235))
    for ring in range(1, 6):
        rr = r * (0.35 + ring * 0.1)
        ddraw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(40, 40, 44, 180), width=2)
    inner_r = r * 0.34
    ddraw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], fill=(222, 210, 180, 255))
    img = Image.alpha_composite(img, disc)
    draw = ImageDraw.Draw(img)
    text = title.strip().upper()
    font, lines, line_h = _fit_multiline(draw, text, font_id, inner_r * 1.6, inner_r * 1.3,
                                          start_size=48, min_size=16, max_lines=3)
    block_h = line_h * len(lines)
    y = cy - block_h / 2
    for line in lines:
        w = draw.textlength(line, font=font)
        x = cx - w / 2
        draw.text((x, y), line, font=font, fill=(20, 16, 10, 255))
        y += line_h
    return img


LAYOUTS = {
    "bottom-banner": {"label": "Bottom Banner", "fn": _layout_bottom_banner, "default_font": "oswald",
                      "description": "Classic scrim band at the bottom, bold centered title."},
    "top-editorial": {"label": "Editorial Corner", "fn": _layout_top_editorial, "default_font": "bebas",
                      "description": "Small eyebrow rule and stacked title top-left, rest left clear."},
    "big-bleed":     {"label": "Poster Bleed", "fn": _layout_big_bleed, "default_font": "anton",
                      "description": "Huge multi-line title filling most of the frame."},
    "center-badge":  {"label": "Center Badge", "fn": _layout_center_badge, "default_font": "playfair",
                      "description": "Calm and minimal - a soft rounded badge centered on the art."},
    "sidebar":       {"label": "Side Bar", "fn": _layout_sidebar, "default_font": "oswald",
                      "description": "Title in a vertical panel on one side, art fills the rest."},
    "vinyl-badge":   {"label": "Vinyl Badge", "fn": _layout_vinyl_badge, "default_font": "pacifico",
                      "description": "Retro record-label badge treatment."},
}
DEFAULT_LAYOUT = "bottom-banner"


def list_layouts():
    return [{"id": k, "label": v["label"], "description": v["description"],
             "default_font": v["default_font"]} for k, v in LAYOUTS.items()]


def composite_title(img, title, layout=DEFAULT_LAYOUT, font_id=None):
    """Draw the playlist title as a real font layer - the one step every
    mode shares, and the one step an image model never performs."""
    layout_meta = LAYOUTS.get(layout, LAYOUTS[DEFAULT_LAYOUT])
    font_id = font_id if font_id in FONTS else layout_meta["default_font"]
    img = _fill_square(img)
    result = layout_meta["fn"](img, title, font_id)
    return result.convert("RGB")


# ---------- prompt building (8-part structure, adapted from the playbook) ----------

# Matches each layout's actual title-safe zone (see the _layout_* functions
# above), so the generated image leaves clear space where the title will
# really land instead of a one-size-fits-all "bottom third" regardless of
# which layout was picked.
_LAYOUT_COMPOSITION_HINTS = {
    "bottom-banner": "leave the bottom third of the frame clear and uncluttered",
    "top-editorial": "leave the top-left quarter of the frame clear and uncluttered",
    "big-bleed": "a bold, simple composition with no fine detail that busy overlaid "
                "lettering would obscure",
    "center-badge": "leave the center of the frame relatively calm and uncluttered",
    "sidebar": "leave one full vertical side of the frame clear and uncluttered, "
              "subject composed toward the other side",
    "vinyl-badge": "leave the lower-center of the frame relatively calm and uncluttered",
}


def build_prompt(playlist_name, track_names, style_id, layout=DEFAULT_LAYOUT):
    style = STYLE_PRESETS.get(style_id, STYLE_PRESETS[DEFAULT_STYLE])
    theme = playlist_name
    if track_names:
        theme += ", featuring songs like " + ", ".join(track_names[:8])
    composition = _LAYOUT_COMPOSITION_HINTS.get(layout, _LAYOUT_COMPOSITION_HINTS[DEFAULT_LAYOUT])
    prompt = (
        f"The photo: {style}, for an album cover. "
        f"Theme and mood inspired by a music playlist called \"{theme}\". "
        f"Composition: {composition}, for a title to be added afterward as a separate "
        "layer. Square format. "
        f"{NO_TEXT_INSTRUCTION}"
    )
    return prompt


# ---------- generation ----------

def generate_template(playlist_id, playlist_name, background_id,
                       layout=DEFAULT_LAYOUT, font_id=None):
    path = _resolve_background_path(background_id)
    with Image.open(path) as bg:
        bg = bg.convert("RGB")
        result = composite_title(bg, playlist_name, layout, font_id)
    return _save_history(playlist_id, result, mode="template",
                          detail={"background_id": background_id, "layout": layout,
                                  "font": font_id or LAYOUTS[layout]["default_font"]})


def generate_ai(playlist_id, playlist_name, track_names, style_id,
                 layout=DEFAULT_LAYOUT, font_id=None):
    if not ai_available():
        raise ReplicateError("REPLICATE_API_TOKEN/REPLICATE_MODEL aren't set.")
    style_id = style_id if style_id in STYLE_PRESETS else DEFAULT_STYLE
    prompt = build_prompt(playlist_name, track_names or [], style_id, layout=layout)
    raw = replicate_client.generate_image(prompt, aspect_ratio="1:1")
    with Image.open(io.BytesIO(raw)) as img:
        result = composite_title(img, playlist_name, layout, font_id)
    return _save_history(playlist_id, result, mode="ai",
                          detail={"style": style_id, "prompt": prompt, "layout": layout,
                                  "font": font_id or LAYOUTS[layout]["default_font"]})


def _save_history(playlist_id, image, mode, detail):
    directory = _covers_dir(playlist_id)
    os.makedirs(directory, exist_ok=True)
    entry_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    filename = f"{entry_id}.png"
    image.save(os.path.join(directory, filename))
    manifest = store.load_json(_manifest_path(playlist_id), [])
    entry = {"id": entry_id, "created": time.time(), "mode": mode, "filename": filename, **detail}
    manifest.insert(0, entry)
    store.save_json(_manifest_path(playlist_id), manifest[:50])
    return entry


def history(playlist_id):
    return store.load_json(_manifest_path(playlist_id), [])


def history_image_path(playlist_id, entry_id):
    manifest = history(playlist_id)
    entry = next((e for e in manifest if e["id"] == entry_id), None)
    if entry is None:
        raise ValueError("no such history entry")
    path = os.path.realpath(os.path.join(_covers_dir(playlist_id), entry["filename"]))
    root = os.path.realpath(_covers_dir(playlist_id))
    if os.path.commonpath([path, root]) != root or not os.path.isfile(path):
        raise ValueError("invalid history entry")
    return path


# ---------- apply / remove ----------

def _resolve_in_library(nd_path):
    """Navidrome and this app conventionally mount the library at the same
    /music path (see README). If Navidrome reports a different root, this
    returns None and apply() falls back to the upload API instead of
    guessing wrong."""
    music_root = cfg.MUSIC_DIR.rstrip("/")
    if nd_path.startswith(music_root + "/"):
        candidate = nd_path
    elif nd_path.startswith("/music/"):
        candidate = os.path.join(music_root, nd_path[len("/music/"):])
    else:
        return None
    real_root = os.path.realpath(music_root)
    real_path = os.path.realpath(candidate)
    if os.path.commonpath([real_path, real_root]) != real_root:
        return None
    return real_path


def _find_playlist_path(playlist_id):
    try:
        playlists = nd.native_playlists()
    except NavidromeError:
        return None
    match = next((p for p in playlists if p.get("id") == playlist_id), None)
    return match.get("path") if match else None


def apply_cover(playlist_id, entry_id):
    image_path = history_image_path(playlist_id, entry_id)
    nd_path = _find_playlist_path(playlist_id)
    local_path = _resolve_in_library(nd_path) if nd_path else None

    if local_path and local_path.lower().endswith(PLAYLIST_FILE_EXTS):
        sidecar = os.path.splitext(local_path)[0] + ".png"
        real_sidecar = os.path.realpath(sidecar)
        real_root = os.path.realpath(cfg.MUSIC_DIR)
        if os.path.commonpath([real_sidecar, real_root]) != real_root:
            raise ValueError("sidecar path escapes the library")
        with open(image_path, "rb") as src, open(real_sidecar, "wb") as dst:
            dst.write(src.read())
        return {"method": "sidecar", "path": real_sidecar}

    with open(image_path, "rb") as fh:
        data = fh.read()
    nd.upload_playlist_image(playlist_id, data, ext="png")
    return {"method": "upload", "playlist_id": playlist_id}


def remove_cover(playlist_id):
    nd_path = _find_playlist_path(playlist_id)
    local_path = _resolve_in_library(nd_path) if nd_path else None
    if local_path and local_path.lower().endswith(PLAYLIST_FILE_EXTS):
        sidecar = os.path.splitext(local_path)[0] + ".png"
        real_sidecar = os.path.realpath(sidecar)
        real_root = os.path.realpath(cfg.MUSIC_DIR)
        if os.path.commonpath([real_sidecar, real_root]) == real_root and os.path.isfile(real_sidecar):
            os.remove(real_sidecar)
            return {"method": "sidecar"}
    nd.delete_playlist_image(playlist_id)
    return {"method": "upload"}
