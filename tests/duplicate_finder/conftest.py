import importlib
import os
import shutil
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session")
def lib(tmp_path_factory):
    """Fixture library + config dir, built once per session."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg is required to build the fixture library")
    import mkfix
    base = tmp_path_factory.mktemp("lib")
    music, config = base / "music", base / "config"
    mkfix.build(str(music))
    return music, config


@pytest.fixture(scope="session")
def app_mod(lib):
    # app.modules.duplicate_finder.service reads its config from the
    # environment at import time - same timing as the original single-file
    # app.py. Auth is disabled for these tests the same way the original
    # app had none; app.main (imported by the `client` fixture) is what
    # wires auth in, so it must come after this env is set too.
    music, config = lib
    os.environ.update(MUSIC_DIR=str(music), CONFIG_DIR=str(config), AUTH_DISABLED="1")
    for k in ("NAVIDROME_URL", "NAVIDROME_USER", "NAVIDROME_PASSWORD", "NAVIDROME_DB",
              "NAVIDROME_MUSIC_ROOT", "LIDARR_URL", "LIDARR_API_KEY"):
        os.environ.pop(k, None)
    return importlib.import_module("app.modules.duplicate_finder.service")


@pytest.fixture(scope="session")
def client(app_mod):
    from fastapi.testclient import TestClient
    main = importlib.import_module("app.main")
    return TestClient(main.app)


@pytest.fixture(scope="session")
def scan(client):
    def run():
        r = client.post("/api/dupes/scan", json={})
        assert r.status_code == 200, r.text
        deadline = time.time() + 60
        while client.get("/api/dupes/scan").json()["status"] == "scanning":
            assert time.time() < deadline, "scan timed out"
            time.sleep(0.05)
        s = client.get("/api/dupes/scan").json()
        assert s["status"] == "done", s["error"]
        return s
    return run
