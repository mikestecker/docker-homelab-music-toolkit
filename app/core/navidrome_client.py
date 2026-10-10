"""Navidrome API client: Subsonic (token auth) for playlist edits, native API
(JWT cookie-style bearer) for the one thing Subsonic can't give you - a
playlist's source file path, which is how Tidarr imports are identified.

Ported from the Subsonic calls in clean-clusters.py, tag-tidarr-playlists.py
and rename-playlists.py (all three built the same request by hand) and the
native login from tag-tidarr-playlists.py. Behavior is unchanged; this just
gives every module one place to call instead of three copies of the same code.
"""
import hashlib
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request

from app.core.config import ND_PASS, ND_URL, ND_USER

SUBSONIC_VERSION = "1.16.1"


class NavidromeError(RuntimeError):
    pass


def _creds(url, user, password):
    return (url or ND_URL).rstrip("/"), user if user is not None else ND_USER, \
        password if password is not None else ND_PASS


def subsonic(endpoint, params=(), client="homelab-music-toolkit",
             url=None, user=None, password=None, timeout=30):
    url, user, password = _creds(url, user, password)
    if not user or not password:
        raise NavidromeError("ND_USER and ND_PASS aren't set (the same Navidrome user "
                              "AudioMuse logs in as).")
    salt = secrets.token_hex(6)
    q = [("u", user), ("t", hashlib.md5((password + salt).encode()).hexdigest()),
         ("s", salt), ("v", SUBSONIC_VERSION), ("c", client), ("f", "json")]
    q.extend((k, str(v)) for k, v in params)
    req_url = f"{url}/rest/{endpoint}?{urllib.parse.urlencode(q)}"
    try:
        with urllib.request.urlopen(req_url, timeout=timeout) as r:
            body = json.load(r)["subsonic-response"]
    except (urllib.error.URLError, OSError) as e:
        raise NavidromeError(f"Navidrome at {url} is unreachable or refused the login: {e}")
    if body.get("status") != "ok":
        err = body.get("error", {})
        raise NavidromeError(f"{endpoint}: {err.get('message', 'failed')} (code {err.get('code')})")
    return body


def ping(**kw):
    return subsonic("ping", **kw)


def get_playlists(**kw):
    return subsonic("getPlaylists", **kw).get("playlists", {}).get("playlist", []) or []


def get_playlist_entries(playlist_id, **kw):
    return subsonic("getPlaylist", [("id", playlist_id)], **kw).get(
        "playlist", {}).get("entry", []) or []


def update_playlist(playlist_id, name=None, comment=None, song_index_to_remove=None, **kw):
    params = [("playlistId", playlist_id)]
    if name is not None:
        params.append(("name", name))
    if comment is not None:
        params.append(("comment", comment))
    if song_index_to_remove is not None:
        params.append(("songIndexToRemove", song_index_to_remove))
    return subsonic("updatePlaylist", params, **kw)


def native_login(url=None, user=None, password=None, timeout=30):
    url, user, password = _creds(url, user, password)
    if not user or not password:
        raise NavidromeError("ND_USER and ND_PASS aren't set.")
    req = urllib.request.Request(
        f"{url}/auth/login", method="POST",
        data=json.dumps({"username": user, "password": password}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        token = json.load(urllib.request.urlopen(req, timeout=timeout)).get("token")
    except (urllib.error.URLError, OSError) as e:
        raise NavidromeError(f"Couldn't log in to Navidrome at {url}: {e}")
    if not token:
        raise NavidromeError("Login refused, check ND_USER and ND_PASS.")
    return token


def native_playlists(url=None, timeout=60):
    """Every playlist with its source file path (native API only)."""
    url = (url or ND_URL).rstrip("/")
    token = native_login(url=url)
    req = urllib.request.Request(
        f"{url}/api/playlist?_start=0&_end=10000&_sort=name&_order=ASC",
        headers={"X-ND-Authorization": f"Bearer {token}"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout))
    except (urllib.error.URLError, OSError) as e:
        raise NavidromeError(f"Couldn't list playlists from Navidrome at {url}: {e}")
