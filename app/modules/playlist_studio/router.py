from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.audiomuse_client import AudioMuseError
from app.core.auth import require_auth
from app.core.navidrome_client import NavidromeError
from app.modules.playlist_studio import service as svc

router = APIRouter(prefix="/api/playlist-studio", tags=["playlist-studio"],
                    dependencies=[Depends(require_auth)])


class Track(BaseModel):
    id: str
    title: str = ""
    artist: str = ""


class GenerateInstantReq(BaseModel):
    prompt: str
    session_id: str | None = None


class GenerateAlchemyReq(BaseModel):
    anchors: list[Track]
    excludes: list[Track] = []
    size: int = 30
    variety: str = "balanced"
    session_id: str | None = None


class RefineReq(BaseModel):
    session_id: str
    instruction: str


class CreateReq(BaseModel):
    session_id: str
    entry_id: str
    playlist_name: str


@router.get("/anchors/search")
def search_anchors(q: str):
    try:
        return {"tracks": svc.search_anchors(q)}
    except NavidromeError as e:
        raise HTTPException(502, str(e))


@router.post("/generate/instant")
def generate_instant(req: GenerateInstantReq):
    try:
        session_id, entry = svc.generate_instant(req.prompt, req.session_id)
    except AudioMuseError as e:
        raise HTTPException(502, str(e))
    return {"session_id": session_id, "entry": entry}


@router.post("/generate/alchemy")
def generate_alchemy(req: GenerateAlchemyReq):
    anchors = [a.model_dump() for a in req.anchors]
    excludes = [e.model_dump() for e in req.excludes]
    try:
        session_id, entry = svc.generate_alchemy(anchors, excludes, req.size, req.variety, req.session_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except AudioMuseError as e:
        raise HTTPException(502, str(e))
    return {"session_id": session_id, "entry": entry}


@router.post("/refine")
def refine(req: RefineReq):
    try:
        entry, diff = svc.refine(req.session_id, req.instruction)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except AudioMuseError as e:
        raise HTTPException(502, str(e))
    return {"entry": entry, "diff": diff}


@router.get("/history/{session_id}")
def get_history(session_id: str):
    return {"history": svc.history(session_id)}


@router.post("/create-playlist")
def create_playlist(req: CreateReq):
    try:
        return svc.create_playlist_from_session(req.session_id, req.entry_id, req.playlist_name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except AudioMuseError as e:
        raise HTTPException(502, str(e))
