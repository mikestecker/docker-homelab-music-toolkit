import json, re, sys, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
PL = [
 {"id": "a", "name": "My Mix 5", "path": "/music/m3u/playlist/My Mix 5.m3u", "comment": "", "sync": True},
 {"id": "b", "name": "🌚Holy Night Drive🌚", "path": "/music/m3u/playlist/🌚Holy Night Drive🌚.m3u", "comment": "", "sync": True},
 {"id": "c", "name": "90s Music", "path": "/music/_playlists/90s Music.nsp", "comment": "", "sync": True},
 {"id": "d", "name": "Skate Session_automatic", "path": "", "comment": ""},
 {"id": "forbidden", "name": "No Upload Rights", "path": "", "comment": ""},
]
IMAGES = {}  # playlist id -> last uploaded image bytes, for round-trip assertions
IMAGE_PATH_RE = re.compile(r"^/api/playlist/([^/]+)/image$")

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, obj, code=200):
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(json.dumps(obj).encode())
    def require_auth(self):
        if self.headers.get("X-ND-Authorization") != "Bearer tok":
            self.send({"error": "unauthorized"}, 401); return False
        return True
    def do_POST(self):
        m = IMAGE_PATH_RE.match(urllib.parse.urlparse(self.path).path)
        if m:
            # Drain the body before any early return - responding without
            # reading a pending request body can reset the connection
            # instead of delivering the response (seen as "Connection reset
            # by peer" on the client, not a clean HTTP 403).
            n = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(n) if n else b""
            if not self.require_auth():
                return
            pid = m.group(1)
            if pid == "forbidden":
                return self.send({"error": "artwork upload is disabled"}, 403)
            ctype = self.headers.get("Content-Type", "")
            boundary = ("--" + ctype.split("boundary=", 1)[1]).encode() if "boundary=" in ctype else b""
            # Minimal multipart extraction: the part between the header blank
            # line and the closing boundary is the uploaded file's bytes.
            if boundary and boundary in body:
                _, _, rest = body.partition(b"\r\n\r\n")
                data, _, _ = rest.rpartition(b"\r\n" + boundary)
                IMAGES[pid] = data
            return self.send({"status": "ok"})
        n = int(self.headers["Content-Length"]); body = json.loads(self.rfile.read(n))
        self.send({"token": "tok"} if body["password"] == "x" else {"error": "bad"})
    def do_DELETE(self):
        m = IMAGE_PATH_RE.match(urllib.parse.urlparse(self.path).path)
        if m:
            if not self.require_auth():
                return
            IMAGES.pop(m.group(1), None)
            return self.send({"status": "ok"})
        self.send({"error": "not found"}, 404)
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        if u.path == "/api/playlist":
            assert self.headers["X-ND-Authorization"] == "Bearer tok"; return self.send(PL)
        if u.path.endswith("updatePlaylist"):
            # Matches real Navidrome's partial-update semantics (core/playlists/
            # playlists.go's Update only touches a field when its pointer arg
            # isn't nil): an omitted param leaves the existing value alone,
            # it doesn't reset it.
            p = next(x for x in PL if x["id"] == q["playlistId"][0])
            if "name" in q: p["name"] = q["name"][0]
            if "comment" in q: p["comment"] = q["comment"][0]
        self.send({"subsonic-response": {"status": "ok"}})
HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
