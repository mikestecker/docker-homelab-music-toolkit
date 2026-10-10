import json, sys, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
PL = [
 {"id": "a", "name": "My Mix 5", "path": "/music/m3u/playlist/My Mix 5.m3u", "comment": "", "sync": True},
 {"id": "b", "name": "🌚Holy Night Drive🌚", "path": "/music/m3u/playlist/🌚Holy Night Drive🌚.m3u", "comment": "", "sync": True},
 {"id": "c", "name": "90s Music", "path": "/music/_playlists/90s Music.nsp", "comment": "", "sync": True},
 {"id": "d", "name": "Skate Session_automatic", "path": "", "comment": ""},
]
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, obj):
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(json.dumps(obj).encode())
    def do_POST(self):
        n = int(self.headers["Content-Length"]); body = json.loads(self.rfile.read(n))
        self.send({"token": "tok"} if body["password"] == "x" else {"error": "bad"})
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        if u.path == "/api/playlist":
            assert self.headers["X-ND-Authorization"] == "Bearer tok"; return self.send(PL)
        if u.path.endswith("updatePlaylist"):
            p = next(x for x in PL if x["id"] == q["playlistId"][0])
            p["name"] = q["name"][0]; p["comment"] = q.get("comment", [""])[0]
        self.send({"subsonic-response": {"status": "ok"}})
HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
