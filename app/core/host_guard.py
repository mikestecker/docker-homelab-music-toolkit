"""Host-allowlist guard, generalized from docker-music-dupes' app.py so it
covers every route in the unified app, not just the duplicate finder's.

DNS rebinding needs a public domain name pointed at your LAN, so by default
only IPs, single-label names and private suffixes get in. Anything else (a
reverse proxy's hostname) has to be listed in ALLOWED_HOSTS.
"""
import ipaddress

from fastapi import Request
from fastapi.responses import JSONResponse, PlainTextResponse

from app.core.config import ALLOWED_HOSTS

LAN_SUFFIXES = (".local", ".lan", ".home", ".home.arpa", ".internal",
                ".localdomain", ".localhost")


def host_allowed(host):
    if "*" in ALLOWED_HOSTS:
        return True
    host = (host or "").strip().lower()
    if host.startswith("["):  # [::1]:8095
        name = host[1:host.find("]")] if "]" in host else ""
    else:
        name = host.rsplit(":", 1)[0] if host.count(":") == 1 else host
    name = name.rstrip(".")
    if not name:
        return False
    if name in ALLOWED_HOSTS:
        return True
    try:
        ipaddress.ip_address(name)
        return True
    except ValueError:
        pass
    return name == "localhost" or "." not in name or name.endswith(LAN_SUFFIXES)


async def request_guard(request: Request, call_next):
    """No auth beyond host checking gets other websites talking to the API.
    Combined with app.core.auth's basic-auth gate for routes that need it."""
    host = request.headers.get("host", "")
    if not host_allowed(host):
        return PlainTextResponse(
            f"This app doesn't answer to the hostname {host!r}. If that's your "
            "reverse proxy, add it to the ALLOWED_HOSTS environment variable.", status_code=403)
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        ctype = request.headers.get("content-type", "").split(";")[0].strip().lower()
        if ctype != "application/json" or request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"detail": "Requests must come from this app's own page."},
                                 status_code=403)
    return await call_next(request)
