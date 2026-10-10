from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import require_auth
from app.modules.playlist_folders import service as svc

router = APIRouter(prefix="/api/playlist-folders", tags=["playlist-folders"],
                    dependencies=[Depends(require_auth)])


class MapReq(BaseModel):
    text: str


class AssignReq(BaseModel):
    old_name: str
    new_full_name: str


@router.get("/map")
def get_map():
    return {"text": svc.get_map_text()}


@router.put("/map")
def put_map(req: MapReq):
    svc.save_map_text(req.text)
    return {"ok": True}


@router.get("/current")
def current():
    return svc.list_playlists_by_folder()


@router.post("/assign")
def assign(req: AssignReq):
    svc.upsert_rule(req.old_name, req.new_full_name)
    return {"ok": True}


@router.post("/preview")
def preview():
    return svc.run(dry_run=True)


@router.post("/apply")
def apply():
    return svc.run(dry_run=False)
