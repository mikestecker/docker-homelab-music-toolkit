from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import require_auth
from app.modules.tidarr_tagging import service as svc

router = APIRouter(prefix="/api/tidarr-tagging", tags=["tidarr-tagging"],
                    dependencies=[Depends(require_auth)])


class SettingsReq(BaseModel):
    prefix: str | None = None
    path_match: str | None = None


class RunReq(BaseModel):
    undo: bool = False


@router.get("/settings")
def get_settings():
    return svc.get_settings()


@router.put("/settings")
def put_settings(req: SettingsReq):
    return svc.save_settings(prefix=req.prefix, path_match=req.path_match)


@router.post("/preview")
def preview(req: RunReq = RunReq()):
    return svc.run(dry_run=True, undo=req.undo)


@router.post("/apply")
def apply(req: RunReq = RunReq()):
    return svc.run(dry_run=False, undo=req.undo)
