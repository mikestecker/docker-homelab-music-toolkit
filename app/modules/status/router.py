"""Status page: Navidrome and AudioMuse reachable and logged in, versions,
playlist counts, last run of each scheduled job.
"""
from fastapi import APIRouter, Depends

from app.core import audiomuse_client
from app.core import navidrome_client as nd
from app.core import scheduler
from app.core.auth import require_auth
from app.core.navidrome_client import NavidromeError

router = APIRouter(prefix="/api/status", tags=["status"], dependencies=[Depends(require_auth)])


@router.get("")
def status():
    nd_status = {"reachable": False, "version": None, "server_version": None,
                 "playlist_count": None, "error": None}
    try:
        ping = nd.ping(client="status")
        nd_status["reachable"] = True
        nd_status["version"] = ping.get("version")
        nd_status["server_version"] = ping.get("serverVersion") or ping.get("type")
        nd_status["playlist_count"] = len(nd.get_playlists(client="status"))
    except NavidromeError as e:
        nd_status["error"] = str(e)

    am_status = {"reachable": audiomuse_client.reachable()}

    return {"navidrome": nd_status, "audiomuse": am_status, "jobs": scheduler.list_jobs()}
