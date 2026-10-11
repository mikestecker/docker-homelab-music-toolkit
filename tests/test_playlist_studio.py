"""Playlist Studio: the pure diff algorithm (no mocks needed), anchor search
against a fake Navidrome, and instant/alchemy/refine generation + history
against a fake AudioMuse - never the real services.
"""
import json
import os
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app.core import config as cfg
from app.modules.playlist_studio import service as svc

MOCKS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mocks")


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
    raise RuntimeError(f"mock server on port {port} never came up")


@pytest.fixture
def studio(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", str(tmp_path / "config"))
    return svc


def track(id_, title, artist):
    return {"id": id_, "title": title, "artist": artist}


# ---------- diff_tracks: pure logic, no I/O ----------

def test_diff_added_only():
    old = [track("1", "A", "X")]
    new = [track("1", "A", "X"), track("2", "B", "Y")]
    d = svc.diff_tracks(old, new)
    assert [t["id"] for t in d["added"]] == ["2"]
    assert d["removed"] == []
    assert {t["id"] for t in d["kept"]} == {"1"}
    assert d["moved"] == []


def test_diff_removed_only():
    old = [track("1", "A", "X"), track("2", "B", "Y")]
    new = [track("1", "A", "X")]
    d = svc.diff_tracks(old, new)
    assert d["added"] == []
    assert [t["id"] for t in d["removed"]] == ["2"]
    assert {t["id"] for t in d["kept"]} == {"1"}


def test_diff_pure_reorder_reports_moved_tracks():
    old = [track("1", "A", "X"), track("2", "B", "Y"), track("3", "C", "Z")]
    new = [track("3", "C", "Z"), track("1", "A", "X"), track("2", "B", "Y")]
    d = svc.diff_tracks(old, new)
    assert d["added"] == [] and d["removed"] == []
    assert {t["id"] for t in d["kept"]} == {"1", "2", "3"}
    # 1 and 2 stayed in relative order (the longest run); 3 is the one that moved.
    assert {t["id"] for t in d["moved"]} == {"3"}


def test_diff_mixed_add_remove_and_reorder():
    old = [track("1", "A", "X"), track("2", "B", "Y"), track("3", "C", "Z")]
    new = [track("2", "B", "Y"), track("4", "D", "W"), track("1", "A", "X")]
    d = svc.diff_tracks(old, new)
    assert [t["id"] for t in d["added"]] == ["4"]
    assert [t["id"] for t in d["removed"]] == ["3"]
    assert {t["id"] for t in d["kept"]} == {"1", "2"}


def test_diff_identical_lists_have_nothing_moved():
    tracks = [track("1", "A", "X"), track("2", "B", "Y")]
    d = svc.diff_tracks(tracks, list(tracks))
    assert d["added"] == [] and d["removed"] == [] and d["moved"] == []
    assert {t["id"] for t in d["kept"]} == {"1", "2"}


def test_diff_tracks_with_no_id_are_never_matched():
    old = [track(None, "Unknown", "")]
    new = [track(None, "Unknown", "")]
    d = svc.diff_tracks(old, new)
    # Can't confirm identity without an id, so each side counts as its own event.
    assert len(d["added"]) == 1
    assert len(d["removed"]) == 1
    assert d["kept"] == []


# ---------- Alchemy prompt composition ----------

def test_alchemy_prompt_needs_at_least_one_anchor():
    with pytest.raises(ValueError):
        svc._alchemy_prompt([], [], 30, "balanced")


def test_alchemy_prompt_includes_anchor_artists_dedup_and_excludes():
    anchors = [track("1", "A", "Kings Kaleidoscope"), track("2", "B", "Kings Kaleidoscope"),
               track("3", "C", "Phil Wickham")]
    excludes = [track("4", "D", "Some Other Band")]
    prompt = svc._alchemy_prompt(anchors, excludes, 40, "balanced")
    assert "Kings Kaleidoscope" in prompt and prompt.count("Kings Kaleidoscope") == 1
    assert "Phil Wickham" in prompt
    assert "Some Other Band" in prompt
    assert "40 songs" in prompt


def test_alchemy_prompt_variety_phrases():
    anchors = [track("1", "A", "Artist")]
    tight = svc._alchemy_prompt(anchors, [], 30, "tight")
    wide = svc._alchemy_prompt(anchors, [], 30, "wide")
    balanced = svc._alchemy_prompt(anchors, [], 30, "balanced")
    assert "predictable" in tight
    assert "unexpected" in wide
    assert "predictable" not in balanced and "unexpected" not in balanced


# ---------- search_anchors against a fake Navidrome ----------

@pytest.fixture
def nd_search_mock(monkeypatch):
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, os.path.join(MOCKS_DIR, "mock_navidrome_search.py"), str(port)])
    _wait_up(port)
    import app.core.navidrome_client as nd
    monkeypatch.setattr(nd, "ND_URL", f"http://127.0.0.1:{port}")
    monkeypatch.setattr(nd, "ND_USER", "mike")
    monkeypatch.setattr(nd, "ND_PASS", "x")
    yield
    proc.kill()
    proc.wait(timeout=5)


def test_search_anchors_finds_matching_tracks(studio, nd_search_mock):
    results = studio.search_anchors("Wickham")
    assert len(results) == 1
    assert results[0] == {"id": "s2", "title": "Desire", "artist": "Phil Wickham"}


def test_search_anchors_empty_query_returns_nothing(studio, nd_search_mock):
    assert studio.search_anchors("   ") == []


# ---------- generation + history against a fake AudioMuse ----------

def am_songs(*songs):
    """Wrap (item_id, title, artist) triples in AudioMuse's real envelope
    shape (response.query_results) - confirmed from a live capture, Oct 2026 -
    the shape audiomuse_client.chat_playlist() actually has to unwrap."""
    return {"response": {"query_results": [
        {"item_id": i, "title": t, "artist": a} for i, t, a in songs
    ]}}


@pytest.fixture
def fake_audiomuse(monkeypatch):
    calls = []
    responses = []  # tests push expected responses; FIFO per chatPlaylist call

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            n = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(n))
            calls.append((self.path, body))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if self.path.endswith("chatPlaylist"):
                resp = responses.pop(0) if responses else am_songs()
            else:
                resp = {"ok": True}
            self.wfile.write(json.dumps(resp).encode())

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    import app.core.audiomuse_client as am
    monkeypatch.setattr(am, "AUDIOMUSE_URL", f"http://127.0.0.1:{srv.server_port}")
    monkeypatch.setattr(am, "AUDIOMUSE_API_TOKEN", "secret")
    yield calls, responses
    srv.shutdown()


def test_generate_instant_saves_history_with_tracks_from_audiomuse(studio, fake_audiomuse):
    calls, responses = fake_audiomuse
    responses.append(am_songs(("1", "Song A", "Band"), ("2", "Song B", "Band")))
    session_id, entry = studio.generate_instant("Upbeat road trip music")
    assert entry["kind"] == "instant"
    assert entry["prompt"] == "Upbeat road trip music"
    assert entry["tracks"] == [
        {"id": "1", "title": "Song A", "artist": "Band", "album": ""},
        {"id": "2", "title": "Song B", "artist": "Band", "album": ""},
    ]
    assert calls[0] == ("/chat/api/chatPlaylist", {"userInput": "Upbeat road trip music"})
    assert studio.history(session_id) == [entry]


def test_generate_alchemy_builds_seed_prompt_and_saves_anchors(studio, fake_audiomuse):
    calls, responses = fake_audiomuse
    responses.append(am_songs(("1", "Higher Throne", "Kings Kaleidoscope")))
    anchors = [track("s1", "Higher Throne", "Kings Kaleidoscope")]
    session_id, entry = studio.generate_alchemy(anchors, [], size=25, variety="wide")
    assert entry["kind"] == "alchemy"
    assert entry["anchors"] == anchors
    sent_prompt = calls[0][1]["userInput"]
    assert "Kings Kaleidoscope" in sent_prompt and "25 songs" in sent_prompt and "unexpected" in sent_prompt


def test_refine_diffs_against_the_prior_entry(studio, fake_audiomuse):
    calls, responses = fake_audiomuse
    responses.append(am_songs(("1", "Song A", "Band"), ("2", "Song B", "Band")))
    session_id, first = studio.generate_instant("Chill evening music")
    responses.append(am_songs(("1", "Song A", "Band"), ("3", "Song C", "Other")))
    entry, diff = studio.refine(session_id, "more upbeat")
    assert entry["kind"] == "refine"
    assert entry["instruction"] == "more upbeat"
    assert "Chill evening music" in entry["prompt"] and "more upbeat" in entry["prompt"]
    assert [t["id"] for t in diff["added"]] == ["3"]
    assert [t["id"] for t in diff["removed"]] == ["2"]
    assert {t["id"] for t in diff["kept"]} == {"1"}
    # Newest entry first.
    assert [e["id"] for e in studio.history(session_id)] == [entry["id"], first["id"]]


def test_refine_without_any_history_raises(studio, fake_audiomuse):
    with pytest.raises(ValueError):
        studio.refine("nonexistent-session", "more upbeat")


def test_refine_requires_a_non_empty_instruction(studio, fake_audiomuse):
    calls, responses = fake_audiomuse
    responses.append(am_songs(("1", "A", "B")))
    session_id, _ = studio.generate_instant("Something")
    with pytest.raises(ValueError):
        studio.refine(session_id, "   ")


def test_create_playlist_from_session_sends_track_ids(studio, fake_audiomuse):
    calls, responses = fake_audiomuse
    responses.append(am_songs(("1", "A", "B"), ("2", "C", "D")))
    session_id, entry = studio.generate_instant("Something")
    studio.create_playlist_from_session(session_id, entry["id"], "Occasions/Test Mix")
    path, body = calls[-1]
    assert path == "/chat/api/create_playlist"
    assert body == {"playlist_name": "Occasions/Test Mix", "item_ids": ["1", "2"]}


def test_create_playlist_from_session_unknown_entry_raises(studio):
    with pytest.raises(ValueError):
        studio.create_playlist_from_session("some-session", "no-such-entry", "Name")
