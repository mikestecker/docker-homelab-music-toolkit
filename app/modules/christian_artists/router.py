from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.auth import require_auth
from app.modules.christian_artists import service as svc

router = APIRouter(prefix="/api/christian-artists", tags=["christian-artists"],
                    dependencies=[Depends(require_auth)])


class SettingsReq(BaseModel):
    prune: bool | None = None


class CsvTextReq(BaseModel):
    text: str


class AddArtistReq(BaseModel):
    artist: str
    genre: str = ""
    worship: str = "no"
    tier: str = "core"
    ambiguous: bool = False
    enabled: bool = True
    mbid: str = ""
    notes: str = ""


class UpdateArtistReq(BaseModel):
    name: str
    genre: str | None = None
    worship: str | None = None
    tier: str | None = None
    ambiguous: str | None = None
    enabled: str | None = None
    mbid: str | None = None
    notes: str | None = None


class NameReq(BaseModel):
    name: str


class BulkAddReq(BaseModel):
    names: list[str]
    genre: str = ""
    worship: str = "no"
    tier: str = "core"
    enabled: bool = True


@router.get("/settings")
def get_settings():
    return svc.get_settings()


@router.put("/settings")
def put_settings(req: SettingsReq):
    return svc.save_settings(prune=req.prune)


@router.get("/artists")
def list_artists():
    return {"rows": svc.get_artist_rows()}


@router.post("/artists")
def add_artist(req: AddArtistReq):
    try:
        return svc.add_artist(req.artist, req.genre, req.worship, req.tier,
                               req.ambiguous, req.enabled, req.mbid, req.notes)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put("/artists")
def update_artist(req: UpdateArtistReq):
    fields = {k: v for k, v in req.model_dump().items() if k != "name"}
    try:
        return svc.update_artist(req.name, **fields)
    except KeyError as e:
        raise HTTPException(404, str(e))


@router.post("/artists/delete")
def delete_artist(req: NameReq):
    try:
        svc.delete_artist(req.name)
    except KeyError as e:
        raise HTTPException(404, str(e))
    return {"ok": True}


@router.post("/artists/bulk")
def bulk_add(req: BulkAddReq):
    return svc.bulk_add(req.names, req.genre, req.worship, req.tier, req.enabled)


@router.get("/csv")
def get_csv_text():
    return {"text": svc.get_artists_text()}


@router.put("/csv")
def put_csv_text(req: CsvTextReq):
    svc.save_artists_text(req.text)
    return {"ok": True}


@router.get("/export")
def export_csv():
    return FileResponse(svc.export_csv_path(), media_type="text/csv",
                         filename="christian-artists.csv")


@router.post("/reset-to-defaults")
def reset_to_defaults():
    return svc.reset_to_defaults()


@router.get("/seed-diff")
def seed_diff():
    return svc.seed_diff()


@router.get("/overrides")
def get_overrides_text():
    return {"text": svc.get_overrides_text(), "warnings": svc.get_overrides_warnings()}


@router.put("/overrides")
def put_overrides_text(req: CsvTextReq):
    svc.save_overrides_text(req.text)
    return {"ok": True, "warnings": svc.get_overrides_warnings()}


@router.get("/migration-log")
def migration_log():
    return svc.migration_log()


@router.get("/scan")
def get_last_scan():
    return svc.last_scan()


@router.post("/scan")
def scan_library():
    return svc.scan_library()


@router.post("/preview")
def preview():
    return svc.run(dry_run=True)


@router.post("/apply")
def apply():
    return svc.run(dry_run=False)
