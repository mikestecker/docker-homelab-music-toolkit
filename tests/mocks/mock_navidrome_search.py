"""Tiny fake Navidrome Subsonic API, just search3, for the playlist studio's
anchor picker."""
import json, sys, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

SONGS = [
    {"id": "s1", "title": "Higher Throne", "artist": "Kings Kaleidoscope"},
    {"id": "s2", "title": "Desire", "artist": "Phil Wickham"},
    {"id": "s3", "title": "Be Still My Soul", "artist": "The Kry"},
]


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        ep = u.path.rsplit("/", 1)[-1]
        r = {"status": "ok"}
        if q.get("u") != ["mike"]:
            r = {"status": "failed", "error": {"code": 40, "message": "Wrong username or password"}}
        elif ep == "search3":
            query = (q.get("query") or [""])[0].lower()
            matches = [s for s in SONGS if query in s["title"].lower() or query in s["artist"].lower()]
            r["searchResult3"] = {"song": matches}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"subsonic-response": r}).encode())


HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
