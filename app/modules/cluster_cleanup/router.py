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
    scope: str | None = None
    reverse_cleanup: bool | None = None


@router.get("/settings")
def get_settings():
    return svc.get_settings()


@router.put("/settings")
def put_settings(req: SettingsReq):
    return svc.save_settings(max_share=req.max_share, min_seconds=req.min_seconds,
                              rename_prefix=req.rename_prefix, scope=req.scope,
                              reverse_cleanup=req.reverse_cleanup)


@router.post("/preview")
def preview():
    return svc.run(dry_run=True)


@router.post("/apply")
def apply():
    return svc.run(dry_run=False)
