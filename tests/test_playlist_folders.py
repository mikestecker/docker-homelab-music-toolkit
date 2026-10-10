"""Playlist folders against a fake Navidrome
(tests/mocks/mock_navidrome_clusters_rename.py), which has a mix of
"_automatic" and plain playlist names to exact- and prefix-match against the
map file.
"""
import pytest

from app.core import config as cfg
from app.modules.playlist_folders import service


@pytest.fixture
def pf(tmp_path, nd_mock, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", str(tmp_path))
    nd_mock("mock_navidrome_clusters_rename.py")
    return service


def test_exact_rule_renames_and_is_idempotent(pf):
    pf.save_map_text("Forgotten Favorites => Smart/Forgotten Favorites\n")
    preview = pf.run(dry_run=True)
    item = next(i for i in preview["items"] if i["name"] == "Forgotten Favorites")
    assert item["new_name"] == "Smart/Forgotten Favorites"

    applied = pf.run(dry_run=False)
    assert applied["changed_count"] == 1
    again = pf.run(dry_run=False)
    assert again["changed_count"] == 0


def test_prefix_rule_renames_every_match(pf):
    # No space before "=>": for prefix rules, trailing whitespace is kept as
    # part of the old prefix (an emoji prefix's trailing space matters), so
    # "Smart/ =>" would require playlists to start with "Smart/ " (extra space).
    pf.save_map_text("prefix: Smart/=>Library/Smart/\n")
    result = pf.run(dry_run=False)
    assert {i["new_name"] for i in result["items"]} == {"Library/Smart/Favorites"}


def test_name_collision_is_skipped(pf):
    pf.save_map_text("Forgotten Favorites => Favorites\n")  # "Favorites" already exists
    result = pf.run(dry_run=True)
    assert result["items"] == []
    assert any("already exists" in line for line in result["log"])


def test_current_groups_by_folder(pf):
    grouped = pf.list_playlists_by_folder()
    assert grouped["error"] is None
    names = {p["name"] for pls in grouped["folders"].values() for p in pls}
    assert "My Favorites" in names
    assert "" in grouped["folders"]  # ungrouped playlists sit at the top level


def test_assign_upserts_the_map_without_duplicating(pf):
    pf.upsert_rule("My Favorites", "Smart/My Favorites")
    assert pf.get_map_text().count("My Favorites =>") == 1
    pf.upsert_rule("My Favorites", "Other/My Favorites")
    text = pf.get_map_text()
    assert text.count("My Favorites =>") == 1
    assert "Other/My Favorites" in text and "Smart/My Favorites" not in text
