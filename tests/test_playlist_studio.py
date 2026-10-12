"""Playlist Studio: the pure diff algorithm (no mocks needed), and anchor
search / instant / alchemy / refine generation + history against a fake
AudioMuse - never the real service. AudioMuse is the only external system
this module talks to now (the anchor picker used to go through Navidrome's
search3, but Alchemy's real API needs AudioMuse's own item_id space, so
anchors are sourced from AudioMuse's /api/search_tracks instead - see
app/modules/playlist_studio/service.py's module docstring).
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from app.core import config as cfg
from app.modules.playlist_studio import service as svc


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


# ---------- fake AudioMuse: chatPlaylist, search_tracks, alchemy ----------

def am_songs(*songs):
    """Wrap (item_id, title, artist) triples in AudioMuse's real chatPlaylist
    envelope shape (response.query_results) - confirmed from a live capture,
    Oct 2026 - the shape audiomuse_client.chat_playlist() actually unwraps."""
    return {"response": {"query_results": [
        {"item_id": i, "title": t, "artist": a} for i, t, a in songs
    ]}}


@pytest.fixture
def fake_audiomuse(monkeypatch):
    calls = []
    responses = []  # tests push expected chatPlaylist/alchemy responses; FIFO
    search_results = []  # what GET /api/search_tracks returns; set directly

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            u = urlparse(self.path)
            params = {k: v[0] for k, v in parse_qs(u.query).items()}
            calls.append((u.path, params))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            body = search_results if u.path == "/api/search_tracks" else []
            self.wfile.write(json.dumps(body).encode())

        def do_POST(self):
            n = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(n))
            calls.append((self.path, body))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if self.path.endswith("chatPlaylist"):
                resp = responses.pop(0) if responses else am_songs()
            elif self.path == "/api/alchemy":
                resp = responses.pop(0) if responses else {"results": []}
            else:
                resp = {"ok": True}
            self.wfile.write(json.dumps(resp).encode())

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    import app.core.audiomuse_client as am
    monkeypatch.setattr(am, "AUDIOMUSE_URL", f"http://127.0.0.1:{srv.server_port}")
    monkeypatch.setattr(am, "AUDIOMUSE_API_TOKEN", "secret")
    yield calls, responses, search_results
    srv.shutdown()


# ---------- audiomuse_client.alchemy(): response-shape fallbacks ----------
# /api/alchemy's response schema isn't documented even in the full OpenAPI
# spec (just "each row contains the song and its centroid") - these lock in
# every shape the parser is meant to tolerate, since a live capture to
# confirm the real one isn't available.

def test_alchemy_parses_results_key(fake_audiomuse):
    calls, responses, _ = fake_audiomuse
    responses.append({"results": [{"item_id": "1", "title": "A", "author": "B"}]})
    import app.core.audiomuse_client as am
    r = am.alchemy([{"id": "x", "op": "ADD", "type": "song"}])
    assert r["songs"] == [{"id": "1", "title": "A", "artist": "B", "album": ""}]
    assert r["raw_response"] == {"results": [{"item_id": "1", "title": "A", "author": "B"}]}


def test_alchemy_falls_back_to_songs_key(fake_audiomuse):
    calls, responses, _ = fake_audiomuse
    responses.append({"songs": [{"item_id": "2", "title": "C", "artist": "D"}]})
    import app.core.audiomuse_client as am
    r = am.alchemy([{"id": "x", "op": "ADD", "type": "song"}])
    assert r["songs"] == [{"id": "2", "title": "C", "artist": "D", "album": ""}]


def test_alchemy_falls_back_to_bare_list(fake_audiomuse):
    calls, responses, _ = fake_audiomuse
    responses.append([{"item_id": "3", "title": "E", "author": "F"}])
    import app.core.audiomuse_client as am
    r = am.alchemy([{"id": "x", "op": "ADD", "type": "song"}])
    assert r["songs"] == [{"id": "3", "title": "E", "artist": "F", "album": ""}]


def test_alchemy_sends_items_n_and_temperature(fake_audiomuse):
    calls, responses, _ = fake_audiomuse
    responses.append({"results": []})
    import app.core.audiomuse_client as am
    am.alchemy([{"id": "x", "op": "ADD", "type": "song"}], n=40, temperature=0.5)
    path, body = calls[0]
    assert path == "/api/alchemy"
    assert body == {"items": [{"id": "x", "op": "ADD", "type": "song"}], "n": 40, "temperature": 0.5}


# ---------- search_anchors, via AudioMuse's own /api/search_tracks ----------

def test_search_anchors_uses_audiomuse_search_tracks(studio, fake_audiomuse):
    calls, responses, search_results = fake_audiomuse
    search_results.append(
        {"item_id": "s1", "title": "Higher Throne", "author": "Kings Kaleidoscope", "album": "Asaph's Arrows II"})
    results = studio.search_anchors("Kaleidoscope")
    assert results == [
        {"id": "s1", "title": "Higher Throne", "artist": "Kings Kaleidoscope", "album": "Asaph's Arrows II"}]
    path, params = calls[0]
    assert path == "/api/search_tracks"
    assert params["search_query"] == "Kaleidoscope"


def test_search_anchors_empty_query_makes_no_call(studio, fake_audiomuse):
    calls, responses, search_results = fake_audiomuse
    assert studio.search_anchors("   ") == []
    assert calls == []


# ---------- generation + history ----------

def test_generate_instant_saves_history_with_tracks_from_audiomuse(studio, fake_audiomuse):
    calls, responses, _ = fake_audiomuse
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


def test_generate_alchemy_needs_at_least_one_anchor(studio, fake_audiomuse):
    with pytest.raises(ValueError):
        studio.generate_alchemy([], [], size=30, variety="balanced")


def test_generate_alchemy_sends_add_and_subtract_items(studio, fake_audiomuse):
    calls, responses, _ = fake_audiomuse
    responses.append({"results": [{"item_id": "1", "title": "Higher Throne", "author": "Kings Kaleidoscope"}]})
    anchors = [track("s1", "Higher Throne", "Kings Kaleidoscope")]
    excludes = [track("s9", "Bad Song", "Nope")]
    session_id, entry = studio.generate_alchemy(anchors, excludes, size=25, variety="wide")
    assert entry["kind"] == "alchemy"
    assert entry["anchors"] == anchors
    assert entry["excludes"] == excludes
    assert entry["variety"] == "wide"
    assert entry["tracks"] == [{"id": "1", "title": "Higher Throne", "artist": "Kings Kaleidoscope", "album": ""}]
    path, body = calls[0]
    assert path == "/api/alchemy"
    assert body["items"] == [
        {"id": "s1", "op": "ADD", "type": "song"},
        {"id": "s9", "op": "SUBTRACT", "type": "song"},
    ]
    assert body["n"] == 25
    assert body["temperature"] == svc.VARIETY_TEMPERATURE["wide"]
    assert studio.history(session_id) == [entry]


def test_refine_diffs_against_the_prior_entry(studio, fake_audiomuse):
    calls, responses, _ = fake_audiomuse
    responses.append(am_songs(("1", "Song A", "Band"), ("2", "Song B", "Band")))
    session_id, first = studio.generate_instant("Chill evening music")
    responses.append(am_songs(("1", "Song A", "Band"), ("3", "Song C", "Other")))
    entry, diff = studio.refine(session_id, "more upbeat")
    assert entry["kind"] == "refine"
    assert entry["instruction"] == "more upbeat"
    assert "Song A by Band" in entry["prompt"] and "more upbeat" in entry["prompt"]
    assert [t["id"] for t in diff["added"]] == ["3"]
    assert [t["id"] for t in diff["removed"]] == ["2"]
    assert {t["id"] for t in diff["kept"]} == {"1"}
    # Newest entry first.
    assert [e["id"] for e in studio.history(session_id)] == [entry["id"], first["id"]]


def test_refine_works_after_an_alchemy_generation(studio, fake_audiomuse):
    """Alchemy entries have no "prompt" field (unlike instant/refine) - refine
    has to build fresh from the track list regardless of how it got there."""
    calls, responses, _ = fake_audiomuse
    responses.append({"results": [{"item_id": "1", "title": "Higher Throne", "author": "Kings Kaleidoscope"}]})
    anchors = [track("s1", "Higher Throne", "Kings Kaleidoscope")]
    session_id, first = studio.generate_alchemy(anchors, [], size=10, variety="balanced")
    assert "prompt" not in first
    responses.append(am_songs(("1", "Higher Throne", "Kings Kaleidoscope"), ("2", "New Song", "Other")))
    entry, diff = studio.refine(session_id, "add more variety")
    assert "Higher Throne by Kings Kaleidoscope" in entry["prompt"]
    assert [t["id"] for t in diff["added"]] == ["2"]


def test_refine_without_any_history_raises(studio, fake_audiomuse):
    with pytest.raises(ValueError):
        studio.refine("nonexistent-session", "more upbeat")


def test_refine_requires_a_non_empty_instruction(studio, fake_audiomuse):
    calls, responses, _ = fake_audiomuse
    responses.append(am_songs(("1", "A", "B")))
    session_id, _entry = studio.generate_instant("Something")
    with pytest.raises(ValueError):
        studio.refine(session_id, "   ")


def test_create_playlist_from_session_sends_track_ids(studio, fake_audiomuse):
    calls, responses, _ = fake_audiomuse
    responses.append(am_songs(("1", "A", "B"), ("2", "C", "D")))
    session_id, entry = studio.generate_instant("Something")
    studio.create_playlist_from_session(session_id, entry["id"], "Occasions/Test Mix")
    path, body = calls[-1]
    assert path == "/chat/api/create_playlist"
    assert body == {"playlist_name": "Occasions/Test Mix", "item_ids": ["1", "2"]}


def test_create_playlist_from_session_unknown_entry_raises(studio):
    with pytest.raises(ValueError):
        studio.create_playlist_from_session("some-session", "no-such-entry", "Name")
