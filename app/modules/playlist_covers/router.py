import mimetypes
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.auth import require_auth
from app.core.navidrome_client import NavidromeError
from app.core.replicate_client import ReplicateError
from app.modules.playlist_covers import service as svc

router = APIRouter(prefix="/api/playlist-covers", tags=["playlist-covers"],
                    dependencies=[Depends(require_auth)])


class GenerateTemplateReq(BaseModel):
    playlist_id: str
    playlist_name: str
    background_id: str
    layout: str = svc.DEFAULT_LAYOUT
    font: str | None = None


class GenerateAIReq(BaseModel):
    playlist_id: str
    playlist_name: str
    style: str | None = None
    include_tracks: bool = True
    layout: str = svc.DEFAULT_LAYOUT
    font: str | None = None


class ApplyReq(BaseModel):
    playlist_id: str
    entry_id: str


class RemoveReq(BaseModel):
    playlist_id: str


@router.get("/playlists")
def list_playlists():
    return svc.list_playlists()


@router.get("/styles")
def list_styles():
    return {"styles": svc.list_styles(), "ai_available": svc.ai_available()}


@router.get("/layouts")
def list_layouts():
    return {"layouts": svc.list_layouts()}


@router.get("/fonts")
def list_fonts():
    return {"fonts": svc.list_fonts()}


@router.get("/backgrounds")
def list_backgrounds():
    return {"backgrounds": svc.list_backgrounds()}


@router.post("/backgrounds")
async def upload_background(file: UploadFile):
    data = await file.read()
    try:
        background_id = svc.save_custom_background(file.filename, data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"background_id": background_id}


@router.get("/backgrounds/image")
def get_background_image(id: str):
    try:
        path = svc._resolve_background_path(id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    media_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type)


@router.post("/generate/template")
def generate_template(req: GenerateTemplateReq):
    try:
        return svc.generate_template(req.playlist_id, req.playlist_name, req.background_id,
                                      layout=req.layout, font_id=req.font)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/generate/ai")
def generate_ai(req: GenerateAIReq):
    tracks = svc.playlist_track_names(req.playlist_id) if req.include_tracks else []
    try:
        return svc.generate_ai(req.playlist_id, req.playlist_name, tracks, req.style,
                                layout=req.layout, font_id=req.font)
    except ReplicateError as e:
        raise HTTPException(502, str(e))


@router.get("/history/{playlist_id}")
def get_history(playlist_id: str):
    return {"history": svc.history(playlist_id)}


@router.get("/history/{playlist_id}/{entry_id}/image")
def get_history_image(playlist_id: str, entry_id: str):
    try:
        path = svc.history_image_path(playlist_id, entry_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return FileResponse(path, media_type="image/png")


@router.post("/apply")
def apply(req: ApplyReq):
    try:
        return svc.apply_cover(req.playlist_id, req.entry_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except NavidromeError as e:
        raise HTTPException(502, str(e))


@router.post("/remove")
def remove(req: RemoveReq):
    try:
        return svc.remove_cover(req.playlist_id)
    except NavidromeError as e:
        raise HTTPException(502, str(e))
