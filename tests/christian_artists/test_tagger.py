import os

import pytest
from mutagen import File as MutagenFile

from app.core import config as cfg
from app.modules.christian_artists import service as svc

from christian_mkfix import FL, M4A, MP3, mk

CSV_HEADER = "artist,genre,worship,tier,ambiguous,enabled,mbid,notes\n"


@pytest.fixture
def lib(tmp_path, monkeypatch):
    music = tmp_path / "music"
    config = tmp_path / "config"
    music.mkdir()
    config.mkdir()
    monkeypatch.setattr(cfg, "MUSIC_DIR", str(music))
    monkeypatch.setattr(cfg, "CONFIG_DIR", str(config))
    svc.save_artists_text(
        CSV_HEADER
        + "Hillsong UNITED,worship,yes,core,no,yes,,\n"
        + "MercyMe,ccm,no,core,no,yes,,\n"
    )
    return str(music)


def _cat(path):
    return svc._get_category(MutagenFile(path))


def test_tags_christian_and_worship_across_formats(lib):
    a = mk(lib, "a.flac", FL, "Hillsong UNITED", album="Al", title="T")
    b = mk(lib, "b.mp3", MP3, "Hillsong UNITED", album="Al", title="T")
    c = mk(lib, "c.m4a", M4A, "Hillsong UNITED", album="Al", title="T")
    result = svc.run(dry_run=False)
    assert result["error"] is None
    assert result["changed"] == 3
    for p in (a, b, c):
        assert _cat(p) == ["christian", "worship"]


def test_tags_christian_only_when_not_worship(lib):
    p = mk(lib, "m.flac", FL, "MercyMe", album="Al", title="T")
    svc.run(dry_run=False)
    assert _cat(p) == ["christian"]


def test_secular_artist_is_not_tagged(lib):
    p = mk(lib, "s.flac", FL, "David Bowie", album="Al", title="T")
    result = svc.run(dry_run=False)
    assert result["changed"] == 0
    assert _cat(p) == []


def test_preserves_foreign_category_values(lib):
    p = mk(lib, "f.flac", FL, "Hillsong UNITED", album="Al", title="T",
           category=["mycustomvalue"])
    svc.run(dry_run=False)
    cats = _cat(p)
    assert "mycustomvalue" in cats
    assert "christian" in cats
    assert "worship" in cats


def test_never_touches_other_tags(lib):
    p = mk(lib, "o.flac", FL, "Hillsong UNITED", album="MyAlbum", title="MyTitle")
    before = dict(MutagenFile(p, easy=True).tags)
    svc.run(dry_run=False)
    after = dict(MutagenFile(p, easy=True).tags)
    for k, v in before.items():
        if k != "category":
            assert after.get(k) == v, k
    assert after.get("title") == before.get("title")
    assert after.get("album") == before.get("album")


def test_apply_is_idempotent_no_rewrite_when_already_correct(lib):
    p = mk(lib, "i.flac", FL, "Hillsong UNITED", album="Al", title="T")
    first = svc.run(dry_run=False)
    assert first["changed"] == 1
    mtime_before = os.stat(p).st_mtime
    second = svc.run(dry_run=False)
    assert second["changed"] == 0
    assert second["unchanged"] == 1
    assert os.stat(p).st_mtime == mtime_before


def test_prune_removes_stale_values_when_artist_removed_from_list(lib):
    p = mk(lib, "p.flac", FL, "Hillsong UNITED", album="Al", title="T")
    svc.run(dry_run=False)
    assert _cat(p) == ["christian", "worship"]
    svc.save_artists_text(CSV_HEADER)  # list is now empty
    result = svc.run(dry_run=False)
    assert result["changed"] == 1
    assert _cat(p) == []


def test_prune_off_keeps_stale_values(lib):
    p = mk(lib, "np.flac", FL, "Hillsong UNITED", album="Al", title="T")
    svc.run(dry_run=False)
    svc.save_artists_text(CSV_HEADER)
    svc.save_settings(prune=False)
    result = svc.run(dry_run=False)
    assert result["changed"] == 0
    assert _cat(p) == ["christian", "worship"]


def test_dry_run_changes_nothing(lib):
    p = mk(lib, "d.flac", FL, "Hillsong UNITED", album="Al", title="T")
    result = svc.run(dry_run=True)
    assert result["changed"] == 1
    assert _cat(p) == []


def test_quarantine_folder_is_skipped(lib):
    p = mk(lib, os.path.join(".dupe-quarantine", "q.flac"), FL,
           "Hillsong UNITED", album="Al", title="T")
    result = svc.run(dry_run=False)
    assert result["changed"] == 0
    assert _cat(p) == []


def test_mbid_match_overrides_disabled_ambiguous_name(lib):
    svc.save_artists_text(
        CSV_HEADER + "Chris Brown,worship,yes,core,yes,yes,confirmed-mbid-1,ambiguous but confirmed\n")
    secular = mk(lib, "secular.flac", FL, "Chris Brown", album="Al", title="T")
    christian = mk(lib, "christian.flac", FL, "Chris Brown", album="Al", title="T2",
                    mbid="confirmed-mbid-1")
    svc.run(dry_run=False)
    assert _cat(secular) == []
    assert _cat(christian) == ["christian", "worship"]


def test_worship_override_applies_during_tagging(lib):
    svc.save_artists_text(CSV_HEADER + "for KING & COUNTRY,ccm,no,core,no,yes,,\n")
    svc.save_overrides_text("for KING & COUNTRY | Burn the Ships | Priceless\n")
    track = mk(lib, "t.flac", FL, "for KING & COUNTRY", album="Burn the Ships", title="Priceless")
    other = mk(lib, "o.flac", FL, "for KING & COUNTRY", album="Burn the Ships", title="Other")
    svc.run(dry_run=False)
    assert _cat(track) == ["christian", "worship"]
    assert _cat(other) == ["christian"]


def test_scan_reports_decision_suggestion_and_counts(lib):
    svc.save_artists_text(
        CSV_HEADER
        + "Hillsong UNITED,worship,yes,core,no,yes,,\n"
        + "Chris Brown,rnb,no,core,yes,no,,ambiguous\n"
        + "Not In Library Band,worship,yes,core,no,yes,,\n"
    )
    mk(lib, "a.flac", FL, "Hillsong UNITED", album="Al", title="T")
    mk(lib, "b.flac", FL, "Hillsong UNITED", album="Al", title="T2")
    mk(lib, "c.flac", FL, "Chris Brown", album="Al", title="T3")
    before = svc.last_scan()
    assert before is None
    result = svc.scan_library()
    assert result["library_counts"]["Hillsong UNITED"] == 2
    assert "Not In Library Band" in result["not_in_library"]
    assert result["needs_decision"][0]["name"] == "Chris Brown"
    assert result["needs_decision"][0]["count"] == 1
    assert svc.last_scan() == result
