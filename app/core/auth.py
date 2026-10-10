"""Shared basic-auth guard. One gate in front of every route: the app holds
your Navidrome admin password and can permanently delete library files, so
every module shares the same auth, not a per-module opt-in.
"""
import secrets

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.core.config import AUTH_DISABLED, AUTH_PASS, AUTH_USER

_basic = HTTPBasic(auto_error=False)


def require_auth(credentials: HTTPBasicCredentials | None = Depends(_basic)):
    if AUTH_DISABLED:
        return True
    if not (AUTH_USER and AUTH_PASS):
        # Misconfigured, not merely "no auth": refuse rather than run open.
        raise HTTPException(500, "AUTH_USER/AUTH_PASS aren't set. Set them, or set "
                                  "AUTH_DISABLED=1 to run without auth on purpose.")
    ok = bool(credentials) and (
        secrets.compare_digest(credentials.username, AUTH_USER)
        and secrets.compare_digest(credentials.password, AUTH_PASS))
    if not ok:
        raise HTTPException(401, "Invalid credentials.", headers={"WWW-Authenticate": "Basic"})
    return True
