"""Session cookie signing (pure, no I/O beyond the one-time secret file) and
the full login/logout/whoami/require_auth flow against the real app via
TestClient - the first dedicated auth test file in this project (previously
every other test just set AUTH_DISABLED=1 to bypass auth entirely, which
remains how the rest of the suite runs and is verified explicitly below).
"""
import importlib
import time

import pytest

from app.core import auth
from app.core import config as cfg
from app.core import sessions


@pytest.fixture
def secret_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(sessions, "_secret_cache", None)
    return tmp_path


# ---------- sessions.py: signing, tampering, expiry ----------

def test_cookie_round_trips(secret_dir):
    value = sessions.create_cookie_value("mike")
    assert sessions.verify_cookie_value(value) == "mike"


def test_tampered_signature_is_rejected(secret_dir):
    value = sessions.create_cookie_value("mike")
    payload, _, sig = value.partition(".")
    flipped = "0" if sig[-1] != "0" else "1"
    assert sessions.verify_cookie_value(f"{payload}.{sig[:-1]}{flipped}") is None


def test_garbage_value_is_rejected(secret_dir):
    assert sessions.verify_cookie_value("not-a-real-cookie") is None
    assert sessions.verify_cookie_value("") is None
    assert sessions.verify_cookie_value(None) is None


def test_expired_cookie_is_rejected(secret_dir, monkeypatch):
    monkeypatch.setattr(sessions, "SESSION_MAX_AGE", 1)
    value = sessions.create_cookie_value("mike")
    time.sleep(1.2)
    assert sessions.verify_cookie_value(value) is None


def test_secret_persists_across_cache_reset(secret_dir):
    first = sessions.create_cookie_value("mike")
    sessions._secret_cache = None  # simulate a fresh process re-reading the file
    assert sessions.verify_cookie_value(first) == "mike"


# ---------- full flow against the real app ----------

@pytest.fixture
def auth_client(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "AUTH_DISABLED", False)
    monkeypatch.setattr(auth, "AUTH_USER", "testuser")
    monkeypatch.setattr(auth, "AUTH_PASS", "testpass")
    monkeypatch.setattr(cfg, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(sessions, "_secret_cache", None)
    from fastapi.testclient import TestClient
    main = importlib.import_module("app.main")
    return TestClient(main.app)


def test_whoami_false_before_login(auth_client):
    assert auth_client.get("/api/auth/whoami").json() == {"authenticated": False}


def test_protected_endpoint_401s_with_no_www_authenticate_header(auth_client):
    r = auth_client.get("/api/prompts/seedprompts")
    assert r.status_code == 401
    assert "www-authenticate" not in {k.lower() for k in r.headers.keys()}


def test_login_wrong_password_401s(auth_client):
    r = auth_client.post("/api/auth/login", json={"username": "testuser", "password": "wrong"})
    assert r.status_code == 401
    assert "session" not in r.cookies


def test_login_sets_cookie_and_unlocks_protected_endpoints(auth_client):
    r = auth_client.post("/api/auth/login", json={"username": "testuser", "password": "testpass"})
    assert r.status_code == 200
    assert "session" in r.cookies
    assert auth_client.get("/api/auth/whoami").json() == {"authenticated": True}
    assert auth_client.get("/api/prompts/seedprompts").status_code == 200


def test_session_cookie_refreshes_on_each_request(auth_client):
    auth_client.post("/api/auth/login", json={"username": "testuser", "password": "testpass"})
    before = auth_client.cookies.get("session")
    r = auth_client.get("/api/prompts/seedprompts")
    assert "session" in r.cookies
    assert r.cookies["session"] != before  # re-signed with a fresh iat


def test_logout_clears_the_session(auth_client):
    auth_client.post("/api/auth/login", json={"username": "testuser", "password": "testpass"})
    assert auth_client.get("/api/auth/whoami").json()["authenticated"] is True
    # json={} rather than a bare POST: the real frontend's api.post() always
    # sends a JSON body (defaults to {}), which is what satisfies host_guard's
    # same-origin check (Content-Type must be application/json) - a bare POST
    # with no body wouldn't set that header and would 403 before auth even
    # runs, which isn't how this endpoint is ever actually called.
    r = auth_client.post("/api/auth/logout", json={})
    assert r.status_code == 200
    assert auth_client.get("/api/auth/whoami").json() == {"authenticated": False}
    assert auth_client.get("/api/prompts/seedprompts").status_code == 401


def test_basic_auth_still_works_with_no_cookie(auth_client):
    import base64
    token = base64.b64encode(b"testuser:testpass").decode()
    r = auth_client.get("/api/prompts/seedprompts", headers={"Authorization": f"Basic {token}"})
    assert r.status_code == 200
    assert "session" not in r.cookies  # the curl/script path never issues a cookie


def test_basic_auth_wrong_password_401s(auth_client):
    import base64
    token = base64.b64encode(b"testuser:wrong").decode()
    r = auth_client.get("/api/prompts/seedprompts", headers={"Authorization": f"Basic {token}"})
    assert r.status_code == 401


def test_auth_disabled_bypasses_everything(auth_client, monkeypatch):
    monkeypatch.setattr(auth, "AUTH_DISABLED", True)
    assert auth_client.get("/api/auth/whoami").json() == {"authenticated": True}
    assert auth_client.get("/api/prompts/seedprompts").status_code == 200


def test_conftest_auth_disabled_bypass_still_works():
    # tests/conftest.py sets AUTH_DISABLED=1 for the whole suite at collection
    # time, and app.core.auth.AUTH_DISABLED was bound from it at first import -
    # confirm that's genuinely still how every other test gets a free pass
    # (unpatched, the real value from conftest), not something this feature
    # quietly broke.
    import os
    from fastapi.testclient import TestClient
    assert os.environ.get("AUTH_DISABLED") == "1"
    assert auth.AUTH_DISABLED is True
    main = importlib.import_module("app.main")
    client = TestClient(main.app)
    assert client.get("/healthz").status_code == 200
    assert client.get("/api/prompts/seedprompts").status_code == 200
