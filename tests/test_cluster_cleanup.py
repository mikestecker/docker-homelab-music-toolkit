"""Cluster cleanup against a fake Navidrome (tests/mocks/mock_navidrome_clusters_rename.py),
which has two "_automatic" clustering playlists plus several non-"_automatic"
playlists that must be left alone, and supports both the songIndexToRemove
and name updatePlaylist calls this module needs.
"""
import pytest

from app.core import config as cfg
from app.modules.christian_artists import service as christian_artists
from app.modules.cluster_cleanup import service

WORSHIP = ["Hillsong UNITED", "Big Tent Revival", "Chris Tomlin", "Elevation Worship",
           "Bethel Music & Jenn Johnson", "Chris Renzema", "John Mark Pantana"]

_CSV_HEADER = "artist,genre,worship,tier,ambiguous,enabled,mbid,notes\n"


@pytest.fixture
def cc(tmp_path, nd_mock, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", str(tmp_path))
    nd_mock("mock_navidrome_clusters_rename.py")
    # A small, fully-controlled artist list, independent of the real
    # christian-artists.csv seed, so this test's behavior doesn't drift if
    # that seed's own classifications ever change.
    rows = _CSV_HEADER + "".join(f"{name},worship,yes,core,no,yes,,\n" for name in WORSHIP)
    christian_artists.save_artists_text(rows)
    return service


def test_only_automatic_playlists_are_considered(cc):
    result = cc.run(dry_run=True)
    assert result["error"] is None
    names = {p["name"] for p in result["playlists"]}
    assert names == {"Skate Session_automatic", "Worship Quiet Morning_automatic"}


def test_minority_worship_is_removed(cc):
    result = cc.run(dry_run=True)
    skate = next(p for p in result["playlists"] if p["name"] == "Skate Session_automatic")
    # "Oceans" (Hillsong UNITED) and "Mend Me (intro)" (Big Tent Revival): 2/20 = 10%.
    assert skate["worship_removed"] == 2
    assert skate["kept_worship_leaning"] is False
    assert result["total_removed"] == 2
    assert any("DRY RUN" in line for line in result["log"])


def test_majority_worship_is_kept(cc):
    result = cc.run(dry_run=True)
    worship = next(p for p in result["playlists"] if p["name"] == "Worship Quiet Morning_automatic")
    # All 5 songs are listed artists: 5/5 = 100%, well over the 34% default.
    assert worship["kept_worship_leaning"] is True
    assert worship["worship_removed"] == 0


def test_apply_is_idempotent(cc):
    applied = cc.run(dry_run=False)
    assert applied["total_removed"] == 2
    again = cc.run(dry_run=False)
    assert again["total_removed"] == 0


def test_settings_roundtrip(cc):
    saved = cc.save_settings(min_seconds=45, max_share=0.5, rename_prefix="AudioMuse/")
    assert saved == {"min_seconds": 45, "max_share": 0.5, "rename_prefix": "AudioMuse/",
                      "scope": "christian", "reverse_cleanup": False}
    assert cc.get_settings() == saved


def test_scope_worship_only_counts_worship_flagged_artists(cc):
    # Big Tent Revival is christian but not worship-flagged in this fixture's
    # list - "worship" scope should leave it (and its minority removal) alone.
    rows = (_CSV_HEADER
            + "Hillsong UNITED,worship,yes,core,no,yes,,\n"
            + "Big Tent Revival,ccm,no,core,no,yes,,\n")
    christian_artists.save_artists_text(rows)
    cc.save_settings(scope="worship")
    result = cc.run(dry_run=True)
    skate = next(p for p in result["playlists"] if p["name"] == "Skate Session_automatic")
    # Only "Oceans" (Hillsong UNITED, worship=yes) counts now - Big Tent
    # Revival is christian but worship=no, so it's out of scope.
    assert skate["worship_removed"] == 1


def test_reverse_cleanup_removes_secular_minority(cc):
    # Every Skate Session artist except Weezer, so that playlist becomes
    # 19/20 (95%) "listed" - a mostly-Christian cluster with one secular
    # straggler (Weezer's "Smile") that reverse_cleanup should remove.
    everyone_but_weezer = ["Sparta", "Thursday", "Big Tent Revival", "Thrice", "Ascend the Hill",
                            "The Kry", "Passion & Kristian Stanfill", "Hillsong UNITED", "Anberlin",
                            "Thousand Foot Krutch", "Project 86", "Switchfoot", "Passion Pit",
                            "Lifehouse", "Chevelle", "Tonic", "Incubus"]
    rows = _CSV_HEADER + "".join(f"{name},rock,no,core,no,yes,,\n" for name in everyone_but_weezer)
    christian_artists.save_artists_text(rows)
    cc.save_settings(reverse_cleanup=True, max_share=0.1)
    result = cc.run(dry_run=True)
    skate = next(p for p in result["playlists"] if p["name"] == "Skate Session_automatic")
    assert skate["kept_worship_leaning"] is True
    assert skate["secular_removed"] == 1
    assert skate["removed_tracks"] == [{"title": "Smile", "artist": "Weezer",
                                         "why": "secular minority", "direction": "secular_minority"}]


def test_rename_prefix_is_applied_once(cc):
    cc.save_settings(rename_prefix="AudioMuse/Clusters/")
    result = cc.run(dry_run=False)
    renamed = {p["name"]: p["renamed_to"] for p in result["playlists"]}
    assert renamed["Skate Session_automatic"] == "AudioMuse/Clusters/Skate Session_automatic"
    assert renamed["Worship Quiet Morning_automatic"] == "AudioMuse/Clusters/Worship Quiet Morning_automatic"
    # The suffix stays, so AudioMuse still finds these playlists next run.
    for new_name in renamed.values():
        assert new_name.endswith(service.SUFFIX)
