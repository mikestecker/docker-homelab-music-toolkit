"""Environment-backed settings shared across modules.

Credentials and connection info come from the environment only, never from
files in the repo (TrueNAS app config sets these). Per-module tuning that the
UI lets you edit (worship artist list, playlist folder map, cleanup
thresholds, job schedules) lives under CONFIG_DIR instead - see each module's
settings store.
"""
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_DEFAULTS_DIR = os.path.join(REPO_ROOT, "config-defaults")

CONFIG_DIR = os.environ.get("CONFIG_DIR", "/config")
MUSIC_DIR = os.path.realpath(os.environ.get("MUSIC_DIR", "/music"))

# Navidrome: the same user AudioMuse logs in as, shared by cluster cleanup,
# Tidarr tagging and playlist folders.
ND_URL = os.environ.get("ND_URL", "").rstrip("/")
ND_USER = os.environ.get("ND_USER", "")
ND_PASS = os.environ.get("ND_PASS", "")

# AudioMuse.
AUDIOMUSE_URL = os.environ.get("AUDIOMUSE_URL", "").rstrip("/")
AUDIOMUSE_API_TOKEN = os.environ.get("AUDIOMUSE_API_TOKEN", "")

# Basic auth. Required by default: this app holds your Navidrome admin
# password and can permanently delete files, so unlike the single-purpose
# apps it was built from, "optional" is the wrong default here. Set
# AUTH_DISABLED=1 to run without it anyway (e.g. behind your own auth proxy).
AUTH_USER = os.environ.get("AUTH_USER", "")
AUTH_PASS = os.environ.get("AUTH_PASS", "")
AUTH_DISABLED = os.environ.get("AUTH_DISABLED", "").strip().lower() in ("1", "true", "yes")

# Hostnames the UI may be reached by, besides IPs, single-label names and
# private suffixes - see core.host_guard. Comma-separated; "*" turns it off.
ALLOWED_HOSTS = {h.strip().lower().rstrip(".") for h in
                 os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()}

TZ = os.environ.get("TZ", "UTC")


def require_auth_configured():
    """True if auth is enabled but AUTH_USER/AUTH_PASS weren't set - a
    misconfiguration worth refusing to start over, not silently running open."""
    return not AUTH_DISABLED and not (AUTH_USER and AUTH_PASS)
