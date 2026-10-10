"""Cluster cleanup against a fake Navidrome (tests/mocks/mock_navidrome_clusters_rename.py),
which has two "_automatic" clustering playlists plus several non-"_automatic"
playlists that must be left alone, and supports both the songIndexToRemove
and name updatePlaylist calls this module needs.
"""
import pytest

from app.core import config as cfg
from app.modules.cluster_cleanup import service

WORSHIP = ["Hillsong UNITED", "Big Tent Revival", "Chris Tomlin", "Elevation Worship",
           "Bethel Music & Jenn Johnson", "Chris Renzema", "John Mark Pantana"]


@pytest.fixture
def cc(tmp_path, nd_mock, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", str(tmp_path))
    nd_mock("mock_navidrome_clusters_rename.py")
    service.save_artists_text("\n".join(WORSHIP) + "\n")
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
    assert saved == {"min_seconds": 45, "max_share": 0.5, "rename_prefix": "AudioMuse/"}
    assert cc.get_settings() == saved


def test_rename_prefix_is_applied_once(cc):
    cc.save_settings(rename_prefix="AudioMuse/Clusters/")
    result = cc.run(dry_run=False)
    renamed = {p["name"]: p["renamed_to"] for p in result["playlists"]}
    assert renamed["Skate Session_automatic"] == "AudioMuse/Clusters/Skate Session_automatic"
    assert renamed["Worship Quiet Morning_automatic"] == "AudioMuse/Clusters/Worship Quiet Morning_automatic"
    # The suffix stays, so AudioMuse still finds these playlists next run.
    for new_name in renamed.values():
        assert new_name.endswith(service.SUFFIX)
