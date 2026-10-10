from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import require_auth
from app.modules.m3u_fix import service as svc

router = APIRouter(prefix="/api/m3u-fix", tags=["m3u-fix"], dependencies=[Depends(require_auth)])


class SettingsReq(BaseModel):
    playlists_dir: str | None = None
    host_music_root: str | None = None


class BackupReq(BaseModel):
    name: str


@router.get("/settings")
def get_settings():
    return svc.get_settings()


@router.put("/settings")
def put_settings(req: SettingsReq):
    try:
        return svc.save_settings(playlists_dir=req.playlists_dir, host_music_root=req.host_music_root)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/preview")
def preview():
    return svc.run(dry_run=True)


@router.post("/apply")
def apply():
    return svc.run(dry_run=False)


@router.get("/backups")
def list_backups():
    return {"backups": svc.list_backups()}


@router.post("/backups/delete")
def delete_backup(req: BackupReq):
    try:
        svc.delete_backup(req.name)
    except (ValueError, OSError) as e:
        raise HTTPException(400, str(e))
    return {"ok": True}
