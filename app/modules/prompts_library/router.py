from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.audiomuse_client import AudioMuseError, chat_playlist, create_playlist
from app.core.auth import require_auth
from app.modules.christian_artists import service as christian_artists
from app.modules.prompts_library import service as svc

router = APIRouter(prefix="/api/prompts", tags=["prompts-library"],
                    dependencies=[Depends(require_auth)])


class RunReq(BaseModel):
    prompt: str
    content_filter: str = "any"


class CreateReq(BaseModel):
    playlist_name: str
    item_ids: list[str]


@router.get("/seedprompts")
def get_seedprompts():
    return svc.seedprompts()


@router.get("/recipes")
def get_recipes():
    return svc.recipes()


@router.get("/newlib")
def get_newlib():
    return svc.newlib()


@router.get("/concepts")
def get_concepts():
    return svc.concepts()


@router.get("/profile")
def get_profile():
    return svc.profile()


@router.post("/run")
def run_prompt(req: RunReq):
    try:
        raw = chat_playlist(req.prompt)
    except AudioMuseError as e:
        raise HTTPException(502, str(e))

    def fetch_more(n):
        return chat_playlist(f"{req.prompt} (give me at least {n} songs)")["songs"]

    result = christian_artists.apply_content_filter(raw["songs"], req.content_filter, fetch_more=fetch_more)
    return {"songs": result["kept"], "filtered_out": result["filtered_out"], "short": result["short"],
            "raw_response": raw["raw_response"]}


@router.get("/suggest-filter")
def suggest_filter(text: str = ""):
    return {"suggestion": christian_artists.suggest_content_filter(text)}


@router.post("/create-playlist")
def create(req: CreateReq):
    try:
        return create_playlist(req.playlist_name, req.item_ids)
    except AudioMuseError as e:
        raise HTTPException(502, str(e))
