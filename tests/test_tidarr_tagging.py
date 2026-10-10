"""Tidarr import filing against a fake Navidrome
(tests/mocks/mock_navidrome_native_api.py), which has two playlists whose
path is under /m3u/playlist/ (Tidarr imports) and two that aren't.
"""
import pytest

from app.core import config as cfg
from app.modules.tidarr_tagging import service


@pytest.fixture
def tt(tmp_path, nd_mock, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", str(tmp_path))
    # The native-API mock's /auth/login only accepts password "x".
    nd_mock("mock_navidrome_native_api.py", password="x")
    return service


def test_preview_finds_only_tidarr_imports(tt):
    result = tt.run(dry_run=True)
    assert result["error"] is None
    names = {i["name"] for i in result["items"]}
    assert names == {"My Mix 5", "\U0001f31aHoly Night Drive\U0001f31a"}
    assert all(i["new_name"].startswith("Imports/Tidarr/") for i in result["items"])
    assert any("DRY RUN" in line for line in result["log"])


def test_apply_tags_and_is_idempotent(tt):
    applied = tt.run(dry_run=False)
    assert applied["changed_count"] == 2
    again = tt.run(dry_run=False)
    assert again["changed_count"] == 0


def test_undo_removes_the_prefix(tt):
    tt.run(dry_run=False)
    undone = tt.run(dry_run=False, undo=True)
    assert undone["changed_count"] == 2
    assert {i["new_name"] for i in undone["items"]} == {"My Mix 5", "\U0001f31aHoly Night Drive\U0001f31a"}


def test_settings_roundtrip(tt):
    saved = tt.save_settings(prefix="📥 ", path_match="/tidarr/")
    assert saved == {"prefix": "📥 ", "path_match": "/tidarr/"}
    assert tt.get_settings() == saved
