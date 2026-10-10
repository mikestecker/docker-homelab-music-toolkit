"""m3u path fixer against a throwaway music folder (no ffmpeg needed - the
matching logic only looks at filenames and folder names, not audio data)."""
import os

import pytest

from app.core import config as cfg
from app.modules.m3u_fix import service


@pytest.fixture
def library(tmp_path):
    music = tmp_path / "music"
    (music / "Artist" / "Album (2019)").mkdir(parents=True)
    (music / "Artist" / "Album (2019)" / "01 Song One.flac").write_bytes(b"a")
    (music / "Artist" / "Album (2019)" / "02 Song Two.flac").write_bytes(b"b")
    pl_dir = music / "m3u" / "playlist"
    pl_dir.mkdir(parents=True)
    return music, pl_dir


@pytest.fixture
def m3u(tmp_path, library, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setattr(cfg, "MUSIC_DIR", str(library[0]))
    # Exercises the setting override itself; the actual value is arbitrary
    # since none of these tests write "host"-style absolute path entries.
    service.save_settings(host_music_root="/mnt/example-legacy-host/music")
    return service


def write_playlist(pl_dir, name, lines):
    (pl_dir / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_broken_relative_path_is_matched_by_title(m3u, library):
    music, pl_dir = library
    # The real file is "01 Song One.flac"; the playlist still points at an
    # old name/extension that no longer exists. A bare relative entry (no
    # leading slash, no "../") is the "library" style in fix-m3u-paths.py.
    write_playlist(pl_dir, "mix.m3u", ["Artist/Album (2019)/01 SongOne.m4a"])
    result = m3u.run(dry_run=True)
    assert result["error"] is None
    pl = result["playlists"][0]
    assert pl["name"] == "mix.m3u"
    assert pl["fixed"][0]["new"] == "Artist/Album (2019)/01 Song One.flac"
    assert pl["backup"] is None  # dry run: nothing written


def test_apply_rewrites_and_keeps_a_backup(m3u, library):
    music, pl_dir = library
    write_playlist(pl_dir, "mix.m3u", ["Artist/Album (2019)/01 SongOne.m4a"])
    result = m3u.run(dry_run=False)
    pl = result["playlists"][0]
    assert pl["backup"] is not None
    new_text = (pl_dir / "mix.m3u").read_text()
    assert "01 Song One.flac" in new_text
    backups = service.list_backups()
    assert pl["backup"] in backups
    service.delete_backup(pl["backup"])
    assert pl["backup"] not in service.list_backups()


def test_existing_valid_entries_are_left_alone(m3u, library):
    music, pl_dir = library
    write_playlist(pl_dir, "clean.m3u", ["Artist/Album (2019)/01 Song One.flac"])
    result = m3u.run(dry_run=True)
    assert result["playlists"] == []  # nothing broken, nothing to report


def test_entry_with_no_match_is_reported_as_missing(m3u, library):
    music, pl_dir = library
    write_playlist(pl_dir, "mix.m3u", ["Artist/Album (2019)/99 Nonexistent.flac"])
    result = m3u.run(dry_run=True)
    pl = result["playlists"][0]
    assert pl["fixed"] == []
    assert pl["missing"][0]["old"] == "Artist/Album (2019)/99 Nonexistent.flac"


def test_backup_delete_refuses_path_outside_playlist_folder(m3u):
    with pytest.raises(ValueError):
        service.delete_backup("../../etc/passwd")


def test_playlists_dir_must_stay_inside_the_library(m3u, tmp_path):
    outside = tmp_path / "not-the-library"
    outside.mkdir()
    with pytest.raises(ValueError):
        service.save_settings(playlists_dir=str(outside))
    # The rejected setting was never persisted.
    assert service.get_settings()["playlists_dir"] != str(outside)


def test_run_refuses_a_hand_edited_out_of_bounds_playlists_dir(m3u, tmp_path, library):
    # Simulate /config being hand-edited directly, bypassing save_settings().
    outside = tmp_path / "not-the-library"
    outside.mkdir()
    from app.core import store
    store.save_json(service._settings_file(), {"playlists_dir": str(outside)})
    result = m3u.run(dry_run=True)
    assert result["error"] == "playlists_dir is outside the music library"
    assert result["playlists"] == []
