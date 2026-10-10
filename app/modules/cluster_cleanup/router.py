from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import require_auth
from app.modules.cluster_cleanup import service as svc

router = APIRouter(prefix="/api/cluster-cleanup", tags=["cluster-cleanup"],
                    dependencies=[Depends(require_auth)])


class SettingsReq(BaseModel):
    max_share: float | None = None
    min_seconds: int | None = None
    rename_prefix: str | None = None


class ArtistsReq(BaseModel):
    text: str


@router.get("/settings")
def get_settings():
    return svc.get_settings()


@router.put("/settings")
def put_settings(req: SettingsReq):
    return svc.save_settings(max_share=req.max_share, min_seconds=req.min_seconds,
                              rename_prefix=req.rename_prefix)


@router.get("/artists")
def get_artists():
    return {"text": svc.get_artists_text()}


@router.put("/artists")
def put_artists(req: ArtistsReq):
    svc.save_artists_text(req.text)
    return {"ok": True}


@router.post("/preview")
def preview():
    return svc.run(dry_run=True)


@router.post("/apply")
def apply():
    return svc.run(dry_run=False)
