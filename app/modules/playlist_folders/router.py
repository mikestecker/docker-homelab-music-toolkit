from fastapi import APIRouter, Depends, HTTPException
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


class CreateFolderReq(BaseModel):
    name: str
    parent_id: str | None = None


class FolderUpdateReq(BaseModel):
    name: str | None = None
    parent_id: str | None = None


class MovePlaylistReq(BaseModel):
    playlist_id: str
    folder_id: str | None = None


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


# --- Folder tree: persisted, nestable, drag-and-drop view -------------------

@router.get("/tree")
def tree():
    return svc.get_tree()


@router.post("/resync")
def resync():
    return svc.resync_tree()


@router.post("/folders")
def create_folder(req: CreateFolderReq):
    try:
        return svc.create_folder(req.name, req.parent_id)
    except KeyError:
        raise HTTPException(404, f"No such folder: {req.parent_id}")


@router.put("/folders/{folder_id}")
def update_folder(folder_id: str, req: FolderUpdateReq):
    body = req.model_dump(exclude_unset=True)
    try:
        result = None
        if "name" in body:
            result = svc.rename_folder(folder_id, body["name"])
        if "parent_id" in body:
            result = svc.move_folder(folder_id, body["parent_id"])
        if result is None:
            raise HTTPException(400, "Nothing to update.")
    except KeyError:
        raise HTTPException(404, f"No such folder: {folder_id}")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return result


@router.post("/folders/{folder_id}/delete")
def delete_folder(folder_id: str):
    try:
        return svc.delete_folder(folder_id)
    except KeyError:
        raise HTTPException(404, f"No such folder: {folder_id}")


@router.post("/move-playlist")
def move_playlist(req: MovePlaylistReq):
    try:
        return svc.move_playlist(req.playlist_id, req.folder_id)
    except KeyError:
        raise HTTPException(404, f"No such folder: {req.folder_id}")
