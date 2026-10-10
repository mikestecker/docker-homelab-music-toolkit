"""Shared fixture for the Navidrome-script modules (cluster_cleanup,
tidarr_tagging, playlist_folders): launches one of tests/mocks/mock_navidrome_*.py
as a real HTTP server and points every Navidrome-touching module at it.

ND_URL/ND_USER/ND_PASS are frozen into app.core.navidrome_client (and, for
the owner-comparison check, into each consuming module) at first import, the
same way the ported scripts' own config was frozen at import time - so
redirecting them per-test means patching those already-bound module
attributes directly, not just setting environment variables.
"""
import os
import socket
import subprocess
import sys
import time

import pytest

# app.core.config freezes AUTH_DISABLED/AUTH_USER/AUTH_PASS at its own first
# import. That can happen during collection (any test module doing `from
# app.core import config`), before any fixture gets a chance to set env vars -
# so this has to be set here, at collection time, not inside a fixture.
os.environ.setdefault("AUTH_DISABLED", "1")

MOCKS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mocks")


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_until_up(port, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"mock server on port {port} never came up")


@pytest.fixture
def nd_mock(monkeypatch):
    procs = []

    def start(script_name, user="mike", password="whatever"):
        port = _free_port()
        proc = subprocess.Popen([sys.executable, os.path.join(MOCKS_DIR, script_name), str(port)])
        procs.append(proc)
        _wait_until_up(port)
        url = f"http://127.0.0.1:{port}"

        import app.core.navidrome_client as nd
        monkeypatch.setattr(nd, "ND_URL", url)
        monkeypatch.setattr(nd, "ND_USER", user)
        monkeypatch.setattr(nd, "ND_PASS", password)
        # Frozen copies in the consuming modules' own namespaces.
        import app.modules.cluster_cleanup.service as cc
        monkeypatch.setattr(cc, "ND_USER", user)
        import app.modules.playlist_folders.service as pf
        monkeypatch.setattr(pf, "ND_USER", user)
        return url

    yield start
    for p in procs:
        p.kill()
        p.wait(timeout=5)
