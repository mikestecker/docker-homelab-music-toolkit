"""Tiny fake Navidrome Subsonic API for testing clean-clusters.py."""
import json, sys, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

S = lambda t, a, d=200: {"title": t, "artist": a, "duration": d}
PL = {
 "1": {"name": "Skate Session_automatic", "owner": "mike", "entry": [
   S("End Moraine", "Sparta"), S("Steps Ascending", "Thursday"), S("Mend Me (intro)", "Big Tent Revival", 62),
   S("Stare at the Sun", "Thrice"), S("Sing", "Ascend the Hill"), S("I Believe It", "The Kry"),
   S("Glorious Day", "Passion & Kristian Stanfill"), S("Smile", "Weezer"), S("Oceans", "Hillsong UNITED"),
   S("Blur", "Thrice"), S("We Owe This to Ourselves", "Anberlin"), S("Shook", "Thousand Foot Krutch"),
   S("Spill Me", "Project 86"), S("Burn Out Bright", "Switchfoot"), S("Passion Song", "Passion Pit"),
   S("Disarray", "Lifehouse"), S("Closure", "Chevelle"), S("Top Falls Down", "Tonic"),
   S("Circles", "Incubus"), S("Kill Me Quickly", "Thrice")]},
 "2": {"name": "Worship Quiet Morning_automatic", "owner": "mike", "entry": [
   S("Holy Forever", "Chris Tomlin"), S("Praise", "Elevation Worship"), S("Goodness", "Bethel Music & Jenn Johnson"),
   S("Springtime", "Chris Renzema"), S("Abba", "John Mark Pantana")]},
 "3": {"name": "My Favorites", "owner": "mike", "entry": [S("Oceans", "Hillsong UNITED")]},
}

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        ep = u.path.rsplit("/", 1)[-1]
        r = {"status": "ok"}
        if q.get("u") != ["mike"]:
            r = {"status": "failed", "error": {"code": 40, "message": "Wrong username or password"}}
        elif ep == "getPlaylists":
            r["playlists"] = {"playlist": [{"id": k, "name": v["name"], "owner": v["owner"], "songCount": len(v["entry"])} for k, v in PL.items()]}
        elif ep == "getPlaylist":
            r["playlist"] = PL[q["id"][0]]
        elif ep == "updatePlaylist":
            PL[q["playlistId"][0]]["entry"].pop(int(q["songIndexToRemove"][0]))
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(json.dumps({"subsonic-response": r}).encode())

HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
