"""Playlist cover art: compositing, backgrounds/fonts/layouts, AI generation
against a fake Replicate server, and the sidecar-vs-upload apply/remove
decision against the fake Navidrome native API.
"""
import os
import socket
import subprocess
import sys
import time

import pytest
from PIL import Image

from app.core import config as cfg
from app.core import replicate_client
from app.modules.playlist_covers import service as svc

MOCKS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mocks")


@pytest.fixture
def covers(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setattr(cfg, "MUSIC_DIR", str(tmp_path / "music"))
    os.makedirs(tmp_path / "music", exist_ok=True)
    return svc


# ---------- listings ----------

def test_lists_150_backgrounds(covers):
    bgs = covers.list_backgrounds()
    assert len(bgs) == 150
    assert all(b["source"] == "builtin" for b in bgs)


def test_lists_seven_fonts(covers):
    assert {f["id"] for f in covers.list_fonts()} == {
        "oswald", "anton", "bebas", "playfair", "caveat", "mono", "pacifico"}


def test_lists_six_layouts(covers):
    assert {l["id"] for l in covers.list_layouts()} == {
        "bottom-banner", "top-editorial", "big-bleed", "center-badge", "sidebar", "vinyl-badge"}


def test_ai_unavailable_without_token(covers, monkeypatch):
    monkeypatch.setattr(cfg, "REPLICATE_API_TOKEN", "")
    assert covers.ai_available() is False


# ---------- compositing ----------

@pytest.mark.parametrize("layout", ["bottom-banner", "top-editorial", "big-bleed",
                                    "center-badge", "sidebar", "vinyl-badge"])
def test_every_layout_produces_a_1024_square(covers, layout):
    bg_id = covers.list_backgrounds()[0]["id"]
    entry = covers.generate_template("pl1", "Test Playlist", bg_id, layout=layout)
    assert entry["layout"] == layout
    img = Image.open(covers.history_image_path("pl1", entry["id"]))
    assert img.size == (covers.SIZE, covers.SIZE)
    assert img.mode == "RGB"


@pytest.mark.parametrize("font_id", ["oswald", "anton", "bebas", "playfair", "caveat", "mono", "pacifico"])
def test_every_font_renders_without_error(covers, font_id):
    bg_id = covers.list_backgrounds()[0]["id"]
    entry = covers.generate_template("pl1", "A Playlist Name", bg_id, font_id=font_id)
    assert entry["font"] == font_id
    assert os.path.isfile(covers.history_image_path("pl1", entry["id"]))


def test_long_title_shrinks_to_fit(covers):
    bg_id = covers.list_backgrounds()[0]["id"]
    entry = covers.generate_template(
        "pl1", "A Very Long Playlist Name That Should Still Fit On The Cover", bg_id,
        layout="bottom-banner")
    assert os.path.isfile(covers.history_image_path("pl1", entry["id"]))


def test_unknown_background_id_is_rejected(covers):
    with pytest.raises(ValueError):
        covers.generate_template("pl1", "Test", "builtin:does-not-exist.jpg")


def test_background_id_path_traversal_is_rejected(covers):
    with pytest.raises(ValueError):
        covers._resolve_background_path("builtin:../../../../etc/passwd")


# ---------- history ----------

def test_history_persists_and_orders_newest_first(covers):
    bg_id = covers.list_backgrounds()[0]["id"]
    e1 = covers.generate_template("pl1", "First", bg_id)
    e2 = covers.generate_template("pl1", "Second", bg_id)
    h = covers.history("pl1")
    assert [e["id"] for e in h] == [e2["id"], e1["id"]]


def test_history_image_path_rejects_unknown_entry(covers):
    with pytest.raises(ValueError):
        covers.history_image_path("pl1", "nonexistent-entry")


# ---------- custom backgrounds ----------

def test_save_custom_background_and_list_it(covers):
    bg_id = covers.save_custom_background("my-bg.jpg", b"fake-jpeg-bytes")
    assert bg_id == "custom:my-bg.jpg"
    assert bg_id in {b["id"] for b in covers.list_backgrounds()}


def test_save_custom_background_rejects_path_traversal(covers):
    with pytest.raises(ValueError):
        covers.save_custom_background("../../etc/passwd", b"x")


# ---------- AI generation against a fake Replicate ----------

def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_up(port, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError("mock Replicate server never came up")


@pytest.fixture
def fake_replicate(monkeypatch):
    port = _free_port()
    proc = subprocess.Popen([sys.executable, os.path.join(MOCKS_DIR, "mock_replicate.py"), str(port)])
    _wait_up(port)
    monkeypatch.setattr(replicate_client, "API_BASE", f"http://127.0.0.1:{port}")
    monkeypatch.setattr(replicate_client, "POLL_INTERVAL", 0.05)
    monkeypatch.setattr(cfg, "REPLICATE_API_TOKEN", "test-token")
    monkeypatch.setattr(cfg, "REPLICATE_MODEL", "test/model")
    monkeypatch.setattr(replicate_client, "REPLICATE_API_TOKEN", "test-token")
    monkeypatch.setattr(replicate_client, "REPLICATE_MODEL", "test/model")
    yield port
    proc.kill()
    proc.wait(timeout=5)


def test_generate_ai_full_pipeline(covers, fake_replicate):
    assert covers.ai_available() is True
    entry = covers.generate_ai("pl1", "Late Night Drive", ["Nightcall by Kavinsky"], "synthwave")
    assert entry["mode"] == "ai"
    assert entry["style"] == "synthwave"
    assert "Do not include any text" in entry["prompt"]
    img = Image.open(covers.history_image_path("pl1", entry["id"]))
    assert img.size == (covers.SIZE, covers.SIZE)


def test_generate_ai_unknown_style_falls_back_to_default(covers, fake_replicate):
    entry = covers.generate_ai("pl1", "Mystery Mix", [], "not-a-real-style")
    assert entry["style"] == covers.DEFAULT_STYLE


def test_build_prompt_always_includes_no_text_instruction(covers):
    for style_id in covers.STYLE_PRESETS:
        prompt = covers.build_prompt("Some Playlist", [], style_id)
        assert "Do not include any text" in prompt
        assert "small thumbnail size" in prompt


# ---------- apply / remove: sidecar vs upload-API ----------

@pytest.fixture
def nd_mock(monkeypatch):
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, os.path.join(MOCKS_DIR, "mock_navidrome_native_api.py"), str(port)])
    _wait_up(port)
    import app.core.navidrome_client as nd
    monkeypatch.setattr(nd, "ND_URL", f"http://127.0.0.1:{port}")
    monkeypatch.setattr(nd, "ND_USER", "mike")
    monkeypatch.setattr(nd, "ND_PASS", "x")
    yield port
    proc.kill()
    proc.wait(timeout=5)


def test_apply_writes_a_sidecar_for_file_backed_playlists(covers, nd_mock, tmp_path):
    # mock playlist "a" has path "/music/m3u/playlist/My Mix 5.m3u"
    pl_dir = tmp_path / "music" / "m3u" / "playlist"
    pl_dir.mkdir(parents=True)
    (pl_dir / "My Mix 5.m3u").write_text("#EXTM3U\n")

    bg_id = covers.list_backgrounds()[0]["id"]
    entry = covers.generate_template("a", "My Mix 5", bg_id)
    result = covers.apply_cover("a", entry["id"])
    assert result["method"] == "sidecar"
    assert (pl_dir / "My Mix 5.png").is_file()

    covers.remove_cover("a")
    assert not (pl_dir / "My Mix 5.png").is_file()


def test_apply_uses_upload_api_for_playlists_with_no_backing_file(covers, nd_mock):
    # mock playlist "d" has path "" (created in Navidrome's UI, no file)
    bg_id = covers.list_backgrounds()[0]["id"]
    entry = covers.generate_template("d", "Skate Session_automatic", bg_id)
    result = covers.apply_cover("d", entry["id"])
    assert result["method"] == "upload"

    removed = covers.remove_cover("d")
    assert removed["method"] == "upload"


def test_upload_api_403_surfaces_a_clear_error(covers, nd_mock):
    # mock playlist "forbidden" always 403s on upload
    bg_id = covers.list_backgrounds()[0]["id"]
    entry = covers.generate_template("forbidden", "No Upload Rights", bg_id)
    with pytest.raises(Exception, match="admin"):
        covers.apply_cover("forbidden", entry["id"])


def test_resolve_in_library_rejects_paths_outside_music_dir(covers):
    assert covers._resolve_in_library("/etc/passwd") is None


def test_resolve_in_library_handles_default_music_convention(covers, tmp_path):
    # Navidrome's own default mount convention is /music, independent of
    # whatever host path cfg.MUSIC_DIR happens to be.
    (tmp_path / "music" / "m3u").mkdir(parents=True)
    resolved = covers._resolve_in_library("/music/m3u/x.m3u")
    assert resolved == str(tmp_path / "music" / "m3u" / "x.m3u")
