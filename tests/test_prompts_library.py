"""Prompts library data access and the AudioMuse "Run in AudioMuse" / create
playlist calls, against a fake AudioMuse server.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app.core import audiomuse_client as am
from app.modules.prompts_library import service


def test_seedprompts_loads_the_bundled_data():
    data = service.seedprompts()
    assert isinstance(data, list) and len(data) > 0
    assert {"name", "prompt"} <= data[0].keys()


def test_recipes_and_newlib_load():
    assert isinstance(service.recipes(), list)
    newlib = service.newlib()
    assert {"recipes", "adds"} <= newlib.keys()


@pytest.fixture
def fake_audiomuse(monkeypatch):
    calls = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            n = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(n))
            calls.append((self.path, self.headers.get("Authorization"), body))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if self.path.endswith("chatPlaylist"):
                # AudioMuse's real response shape, confirmed from a live
                # capture (Oct 2026): everything nested under response, the
                # song list at query_results keyed item_id/title/artist.
                self.wfile.write(json.dumps({"response": {
                    "query_results": [{"item_id": "1", "title": "Song", "artist": "Band", "album": "Album"}],
                }}).encode())
            else:
                self.wfile.write(json.dumps({"ok": True}).encode())

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setattr(am, "AUDIOMUSE_URL", f"http://127.0.0.1:{srv.server_port}")
    monkeypatch.setattr(am, "AUDIOMUSE_API_TOKEN", "secret-token")
    yield calls
    srv.shutdown()


def test_chat_playlist_sends_prompt_and_token(fake_audiomuse):
    result = am.chat_playlist("Upbeat summer country for a pool day")
    assert result["songs"] == [{"id": "1", "title": "Song", "artist": "Band", "album": "Album"}]
    assert "response" in result["raw_response"]  # the original envelope stays available
    path, auth, body = fake_audiomuse[0]
    assert path == "/chat/api/chatPlaylist"
    assert auth == "Bearer secret-token"
    assert body == {"userInput": "Upbeat summer country for a pool day"}


def test_create_playlist_sends_name_and_ids(fake_audiomuse):
    am.create_playlist("Occasions/Summer/Pool Day", ["1", "2", "3"])
    path, auth, body = fake_audiomuse[0]
    assert path == "/chat/api/create_playlist"
    assert body == {"playlist_name": "Occasions/Summer/Pool Day", "item_ids": ["1", "2", "3"]}


def test_audiomuse_error_surfaces_the_status_code(monkeypatch):
    monkeypatch.setattr(am, "AUDIOMUSE_URL", "http://127.0.0.1:1")  # nothing listening
    with pytest.raises(am.AudioMuseError):
        am.chat_playlist("x")
