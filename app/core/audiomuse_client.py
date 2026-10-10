"""AudioMuse-AI API client.

Confirmed facts (from AudioMuse's source, Oct 2026 - re-check against
/apidocs/ if these ever 404):
  POST /chat/api/chatPlaylist   {"userInput": "<prompt>"} -> Instant Playlist songs
  POST /chat/api/create_playlist  {"playlist_name": ..., "item_ids": [...]} -> creates it
Song Alchemy (/api/alchemy) and anchors/radios aren't wired up yet - v1 scope
is the prompts library's "Run in AudioMuse" button only.
"""
import json
import urllib.error
import urllib.request

from app.core.config import AUDIOMUSE_API_TOKEN, AUDIOMUSE_URL


class AudioMuseError(RuntimeError):
    pass


def _post(path, payload, timeout=60):
    if not AUDIOMUSE_URL:
        raise AudioMuseError("AUDIOMUSE_URL isn't set.")
    req = urllib.request.Request(
        f"{AUDIOMUSE_URL}{path}", method="POST",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {AUDIOMUSE_API_TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise AudioMuseError(f"AudioMuse returned {e.code} for {path}: {detail[:300]}")
    except (urllib.error.URLError, OSError) as e:
        raise AudioMuseError(f"AudioMuse at {AUDIOMUSE_URL} is unreachable: {e}")


def chat_playlist(user_input):
    """Run Instant Playlist. Max 200 songs; a size in the prompt overrides the
    Number of songs setting; seed songs are left out of the results; results
    are reordered by tempo, energy and key (see the playbook)."""
    return _post("/chat/api/chatPlaylist", {"userInput": user_input})


def create_playlist(playlist_name, item_ids):
    return _post("/chat/api/create_playlist",
                  {"playlist_name": playlist_name, "item_ids": item_ids})


def reachable(timeout=5):
    """Best-effort reachability for the status page. AudioMuse has no
    documented health endpoint, so this just checks the server answers."""
    try:
        req = urllib.request.Request(f"{AUDIOMUSE_URL}/apidocs/")
        urllib.request.urlopen(req, timeout=timeout)
        return True
    except Exception:
        return False
