"""App factory: mounts every module's router under its own /api/<module>
prefix, wires the app-wide host-allowlist middleware (app/core/host_guard.py)
and basic-auth gate (app/core/auth.py, applied per-router), registers the
jobs the scheduler can run unattended, and serves the built React frontend.
"""
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core import scheduler
from app.core.config import require_auth_configured
from app.core.host_guard import request_guard
from app.modules.cluster_cleanup import service as cluster_cleanup_service
from app.modules.cluster_cleanup.router import router as cluster_cleanup_router
from app.modules.duplicate_finder.router import router as duplicate_finder_router
from app.modules.m3u_fix.router import router as m3u_fix_router
from app.modules.playlist_folders.router import router as playlist_folders_router
from app.modules.prompts_library.router import router as prompts_library_router
from app.modules.scheduler.router import router as jobs_router
from app.modules.status.router import router as status_router
from app.modules.tidarr_tagging import service as tidarr_tagging_service
from app.modules.tidarr_tagging.router import router as tidarr_tagging_router

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIST = os.path.join(APP_ROOT, "frontend", "dist")

if require_auth_configured():
    # Fail fast rather than quietly running open: this app holds your
    # Navidrome admin password and can permanently delete library files.
    raise SystemExit("AUTH_USER/AUTH_PASS aren't set. Set them in your environment, or "
                      "set AUTH_DISABLED=1 to run without auth on purpose (e.g. behind "
                      "your own auth proxy).")

app = FastAPI(title="homelab-music-toolkit")
app.middleware("http")(request_guard)

for _router in (duplicate_finder_router, cluster_cleanup_router, tidarr_tagging_router,
                playlist_folders_router, m3u_fix_router, prompts_library_router,
                jobs_router, status_router):
    app.include_router(_router)


@app.get("/healthz")
def healthz():
    return {"ok": True}


# Jobs the scheduler can run unattended. Each run always does the real apply
# (dry_run=False) - previewing on a schedule would just silently do nothing.
scheduler.register("cluster_cleanup", "Cluster cleanup",
                    lambda: cluster_cleanup_service.run(dry_run=False))
scheduler.register("tidarr_tagging", "Tidarr import filing",
                    lambda: tidarr_tagging_service.run(dry_run=False, undo=False))
scheduler.start()

# The built React SPA, when present (the production Docker image builds it).
# In development, run `npm run dev` in frontend/ and use the Vite dev server
# instead - this app serves the API either way.
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        # Without this check, any typo'd or deprecated /api/* path silently
        # falls through to here and returns 200 HTML instead of a real 404 -
        # harmless, but confusing to debug and masks real routing mistakes.
        if full_path == "healthz" or full_path.startswith(("api/", "assets/")):
            raise HTTPException(404)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
