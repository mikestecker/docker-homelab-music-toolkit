"""Tiny ffmpeg-generated audio fixtures for the Christian artists tagger -
FLAC/MP3/M4A, following tests/duplicate_finder/mkfix.py's mk() pattern.

CATEGORY and MusicBrainz artist id aren't standard tags ffmpeg's muxers will
write from a plain -metadata flag on every format (confirmed: ffmpeg's MP3/
M4A muxers silently drop an unrecognized custom key), so those two are
written in a second pass using mutagen directly - the same format-specific
TXXX/FreeForm writer the tagger itself uses (app.modules.christian_artists.
service._set_category) for CATEGORY, and mutagen's easy-tag writer (which
*does* map musicbrainz_artistid correctly on every format) for the mbid.
"""
import os
import subprocess

from mutagen import File as MutagenFile

from app.modules.christian_artists.service import _set_category

FL = ["-c:a", "flac"]
MP3 = ["-c:a", "libmp3lame", "-b:a", "192k"]
M4A = ["-c:a", "aac", "-b:a", "192k"]


def mk(root, path, codec, artist, album="", title="", albumartist=None,
       category=None, mbid=None, mtime=None, duration=2):
    p = os.path.join(root, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    md = {"artist": artist, "album": album, "title": title or os.path.splitext(os.path.basename(path))[0]}
    if albumartist is not None:
        md["album_artist"] = albumartist
    args = ["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi",
            "-i", f"sine=f=440:d={duration}"] + codec
    for k, v in md.items():
        args += ["-metadata", f"{k}={v}"]
    subprocess.run(args + [p], check=True)

    if mbid:
        f = MutagenFile(p, easy=True)
        f["musicbrainz_artistid"] = [mbid]
        f.save()
    if category:
        values = list(category) if isinstance(category, (list, tuple)) else [category]
        f = MutagenFile(p)
        _set_category(f, values)

    if mtime:
        os.utime(p, (mtime, mtime))
    return p
