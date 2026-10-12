"""Signed session cookies for the login page - stateless (no server-side
session store), stdlib-only (hmac/hashlib/secrets), matching this app's
pure-stdlib client convention.

The signing secret is generated once (secrets.token_hex) and persisted under
CONFIG_DIR, the same seed-once-then-persist pattern every other /config
value in this app uses (app.core.store) - no new env var needed, and it
survives restarts as long as the config volume does.
"""
import base64
import hashlib
import hmac
import json
import os
import time

from app.core import config as cfg
from app.core import store

SESSION_COOKIE_NAME = "session"
SESSION_MAX_AGE = 60 * 60 * 24 * 21  # 3 weeks

_secret_cache = None


def _secret_path():
    return os.path.join(cfg.CONFIG_DIR, "session-secret.txt")


def _secret():
    global _secret_cache
    if _secret_cache is None:
        import secrets as _secrets
        existing = store.load_text(_secret_path(), "").strip()
        if existing:
            _secret_cache = existing
        else:
            _secret_cache = _secrets.token_hex(32)
            store.save_text(_secret_path(), _secret_cache)
    return _secret_cache


def _sign(payload_b64):
    return hmac.new(_secret().encode(), payload_b64.encode(), hashlib.sha256).hexdigest()


def create_cookie_value(username):
    payload = json.dumps({"u": username, "iat": time.time()}).encode()
    payload_b64 = base64.urlsafe_b64encode(payload).decode()
    return f"{payload_b64}.{_sign(payload_b64)}"


def verify_cookie_value(value):
    """Returns the username if the cookie is validly signed and not expired,
    else None. Signature comparison is constant-time, matching the same
    discipline app.core.auth already uses for Basic Auth."""
    if not value or "." not in value:
        return None
    payload_b64, _, signature = value.partition(".")
    if not hmac.compare_digest(_sign(payload_b64), signature):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()))
        username, issued_at = payload["u"], float(payload["iat"])
    except (ValueError, KeyError, TypeError):
        return None
    if issued_at + SESSION_MAX_AGE < time.time():
        return None
    return username
