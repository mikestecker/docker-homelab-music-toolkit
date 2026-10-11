"""Tiny fake Replicate API: POST .../predictions starts a "prediction" that
reports processing once, then succeeded, with output pointing back at this
same server's /fake-image.png (a real 2x2 PNG, built with Pillow rather than
hand-written bytes) - enough to exercise the client's full
submit/poll/download cycle without a real API call.
"""
import io
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

from PIL import Image

STATE = {"calls": 0, "last_prompt": None, "last_path": None}
_buf = io.BytesIO()
Image.new("RGB", (2, 2), (200, 50, 50)).save(_buf, format="PNG")
TINY_PNG = _buf.getvalue()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send_json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n)) if n else {}
        if self.path.endswith("/predictions"):
            if self.headers.get("Authorization") != "Token test-token":
                return self.send_json({"detail": "unauthorized"}, 401)
            STATE["last_prompt"] = body.get("input", {}).get("prompt")
            STATE["last_path"] = self.path
            STATE["calls"] = 0
            return self.send_json({"id": "pred1", "status": "starting"})
        self.send_json({"detail": "not found"}, 404)

    def do_GET(self):
        if self.path == "/predictions/pred1":
            STATE["calls"] += 1
            if STATE["calls"] < 2:
                return self.send_json({"id": "pred1", "status": "processing"})
            host = self.headers.get("Host", "127.0.0.1")
            return self.send_json({"id": "pred1", "status": "succeeded",
                                   "output": [f"http://{host}/fake-image.png"]})
        if self.path == "/fake-image.png":
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(TINY_PNG)))
            self.end_headers()
            self.wfile.write(TINY_PNG)
            return
        self.send_json({"detail": "not found"}, 404)


HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
