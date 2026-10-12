"""Shared auth guard. One gate in front of every route: the app holds your
Navidrome admin password and can permanently delete library files, so every
module shares the same auth, not a per-module opt-in.

Two ways in, both checked by require_auth:
  - A signed session cookie (app.core.sessions), issued by POST /api/auth/login
    and refreshed on every authenticated request (a sliding ~3-week window).
    This is what the frontend's login page uses.
  - HTTP Basic Auth credentials, checked exactly as before - kept as a
    fallback for curl/scripts, not used by the browser UI anymore.
On failure, the response deliberately omits WWW-Authenticate: Basic - that
header is what triggers the browser's native Basic Auth popup, and the whole
point of this module is that the UI shows its own login page instead.
"""
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

from app.core import sessions
from app.core.config import AUTH_DISABLED, AUTH_PASS, AUTH_USER

_basic = HTTPBasic(auto_error=False)


def _auth_configured():
    return bool(AUTH_USER and AUTH_PASS)


def _require_configured():
    if not _auth_configured():
        # Misconfigured, not merely "no auth": refuse rather than run open.
        raise HTTPException(500, "AUTH_USER/AUTH_PASS aren't set. Set them, or set "
                                  "AUTH_DISABLED=1 to run without auth on purpose.")


def _credentials_valid(username, password):
    return bool(username and password and
                secrets.compare_digest(username, AUTH_USER)
                and secrets.compare_digest(password, AUTH_PASS))


def _session_username(request: Request):
    return sessions.verify_cookie_value(request.cookies.get(sessions.SESSION_COOKIE_NAME))


def require_auth(request: Request, response: Response,
                  credentials: HTTPBasicCredentials | None = Depends(_basic)):
    if AUTH_DISABLED:
        return True
    _require_configured()

    if _session_username(request):
        # Sliding expiry: every authenticated request re-issues the cookie,
        # resetting both the embedded timestamp and the browser's own expiry.
        response.set_cookie(sessions.SESSION_COOKIE_NAME, sessions.create_cookie_value(AUTH_USER),
                             max_age=sessions.SESSION_MAX_AGE, httponly=True, samesite="lax")
        return True

    if credentials and _credentials_valid(credentials.username, credentials.password):
        return True  # curl/script path - no cookie issued, not the browser flow

    raise HTTPException(401, "Invalid credentials.")


router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginReq(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(req: LoginReq, response: Response):
    if AUTH_DISABLED:
        return {"ok": True}
    _require_configured()
    if not _credentials_valid(req.username, req.password):
        raise HTTPException(401, "Invalid username or password.")
    response.set_cookie(sessions.SESSION_COOKIE_NAME, sessions.create_cookie_value(AUTH_USER),
                         max_age=sessions.SESSION_MAX_AGE, httponly=True, samesite="lax")
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(sessions.SESSION_COOKIE_NAME)
    return {"ok": True}


@router.get("/whoami")
def whoami(request: Request, credentials: HTTPBasicCredentials | None = Depends(_basic)):
    if AUTH_DISABLED or not _auth_configured():
        return {"authenticated": True}
    authenticated = bool(_session_username(request)) or bool(
        credentials and _credentials_valid(credentials.username, credentials.password))
    return {"authenticated": authenticated}
