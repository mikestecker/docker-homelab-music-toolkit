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


# --- Folder tree: persisted, nestable, drag-and-drop model ------------------

def test_create_rename_move_delete_folder(pf):
    root = pf.create_folder("Occasions")
    child = pf.create_folder("Summer", parent_id=root["id"])
    assert child["parent_id"] == root["id"]

    pf.move_playlist("3", child["id"])  # "My Favorites"
    moved = next(p for p in pf.get_tree()["playlists"] if p["id"] == "3")
    assert moved["name"] == "Occasions/Summer/My Favorites"
    assert moved["folder_id"] == child["id"]

    pf.rename_folder(root["id"], "Events")
    moved = next(p for p in pf.get_tree()["playlists"] if p["id"] == "3")
    assert moved["name"] == "Events/Summer/My Favorites"

    pf.move_folder(child["id"], None)  # unnest Summer to root
    moved = next(p for p in pf.get_tree()["playlists"] if p["id"] == "3")
    assert moved["name"] == "Summer/My Favorites"

    pf.delete_folder(root["id"])
    assert all(f["id"] != root["id"] for f in pf.get_tree()["folders"])


def test_move_folder_rejects_cycle(pf):
    parent = pf.create_folder("Parent")
    child = pf.create_folder("Child", parent_id=parent["id"])
    with pytest.raises(ValueError):
        pf.move_folder(parent["id"], child["id"])


def test_delete_folder_reparents_children(pf):
    parent = pf.create_folder("Parent")
    child_folder = pf.create_folder("Child", parent_id=parent["id"])
    pf.move_playlist("5", parent["id"])  # "Forgotten Favorites"

    pf.delete_folder(parent["id"])

    tree = pf.get_tree()
    cf = next(f for f in tree["folders"] if f["id"] == child_folder["id"])
    assert cf["parent_id"] is None
    moved = next(p for p in tree["playlists"] if p["id"] == "5")
    assert moved["name"] == "Forgotten Favorites"
    assert moved["folder_id"] is None


def test_move_playlist_rejects_collision(pf):
    # id 6 is "Smart/Favorites"; id 7 is "Favorites" - moving 6 to root collides.
    result = pf.move_playlist("6", None)
    assert result["ok"] is False
    assert "already exists" in result["error"]


def test_tree_is_seeded_from_existing_playlist_names(pf):
    tree = pf.get_tree()
    smart = next(f for f in tree["folders"] if f["name"] == "Smart")
    fav = next(p for p in tree["playlists"] if p["id"] == "6")
    assert fav["folder_id"] == smart["id"]
    assert any(p["id"] == "7" and p["folder_id"] is None for p in tree["playlists"])


def test_resync_rebuilds_tree_from_current_names(pf):
    pf.create_folder("Scratch")
    result = pf.resync_tree()
    assert all(f["name"] != "Scratch" for f in result["folders"])
    assert any(f["name"] == "Smart" for f in result["folders"])
