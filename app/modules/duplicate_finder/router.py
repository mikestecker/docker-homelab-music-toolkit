"""FastAPI routes for the duplicate finder, ported from docker-music-dupes'
app.py. Endpoint paths and payloads are unchanged except for the /api/dupes
prefix (this app hosts several modules, so every module gets its own
prefix instead of one flat /api/ namespace). Host-allowlisting and the
JSON-only-POST guard are now app-wide (app/core/host_guard.py); auth is
app-wide too (app/core/auth.py) instead of "no auth, LAN only".
"""
import os
import shutil
import threading
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.auth import require_auth
from app.modules.duplicate_finder import service as svc

router = APIRouter(prefix="/api/dupes", tags=["duplicate-finder"], dependencies=[Depends(require_auth)])


class ScanReq(BaseModel):
    mode: str | None = None  # ignored; older pages still send it


class PathsReq(BaseModel):
    paths: list[str]


class UpgradeReq(BaseModel):
    rel: str


class BatchReq(BaseModel):
    batch: str


class KeepBothReq(BaseModel):
    key: str
    kept: bool = True


@router.get("/info")
def info():
    return {"music": svc.MUSIC, "quarantine": svc.QDIR,
            "lidarr": bool(svc.LIDARR_URL and svc.LIDARR_KEY),
            "fingerprint": svc.FINGERPRINT if svc.FPCALC else "off",
            "fp_workers": svc.FP_WORKERS}


@router.get("/scan")
def scan_state():
    with svc.LOCK:
        return dict(svc.STATE)


@router.post("/scan")
def start_scan(req: ScanReq | None = None):
    with svc.LOCK:
        if svc.STATE["status"] == "scanning":
            raise HTTPException(409, "A scan is already running.")
        svc.STATE.update(status="scanning", scan_id=uuid.uuid4().hex,
                          phase="Starting", skip_fp=False, scanned=0, total=0, unreadable=0,
                          started=time.time(), finished=None, error=None,
                          warnings=[], clusters=[])
    threading.Thread(target=svc.run_scan, daemon=True).start()
    return {"ok": True}


@router.post("/scan/skip-fingerprints")
def skip_fingerprints(req: ScanReq | None = None):
    with svc.LOCK:
        if svc.STATE["status"] != "scanning":
            raise HTTPException(409, "No scan is running.")
        svc.STATE["skip_fp"] = True
    return {"ok": True}


@router.get("/audio")
def audio(rel: str):
    try:
        p = svc.library_path(rel)
    except ValueError:
        raise HTTPException(400, "That path is outside the library.")
    if not os.path.isfile(p):
        raise HTTPException(404, "That file isn't there anymore.")
    ext = os.path.splitext(p)[1].lower().lstrip(".")
    return FileResponse(p, media_type=svc.MIME.get(ext, "application/octet-stream"))


@router.post("/keep-both")
def keep_both(req: KeepBothReq):
    with svc.MLOCK:
        kept = set(svc.load_json(svc.IGNORED, []))
        (kept.add if req.kept else kept.discard)(req.key)
        svc.save_json(svc.IGNORED, sorted(kept))
    with svc.LOCK:
        for c in svc.STATE["clusters"]:
            if c["key"] == req.key:
                c["ignored"] = req.kept
    return {"ok": True}


@router.post("/quarantine")
def quarantine(req: PathsReq):
    # MLOCK for the whole operation: two overlapping requests must not both
    # pass the one-copy guard for the same track.
    with svc.MLOCK:
        with svc.LOCK:
            if svc.STATE["status"] != "done":
                raise HTTPException(409, "Run a scan first.")
            rows = [r for c in svc.STATE["clusters"] for r in c["rows"]]
        wanted = set(req.paths)
        plan, errors = [], []
        for r in rows:
            live = [f for f in r["files"] if not f["moved"]]
            picks = [f for f in live if f["rel"] in wanted]
            if not picks:
                continue
            keep = [f for f in live if f not in picks and svc.unchanged(f)]
            if not keep:
                errors.append(f"Skipped {r['title']}: no other copy would be left, "
                              "or it changed since the scan. Scan again.")
                continue
            for f in picks:
                if svc.unchanged(f):
                    plan.append(f)
                else:
                    errors.append(f"Skipped {f['rel']}: it changed or moved since the scan. "
                                  "Scan again.")
        if not plan:
            return {"batch": None, "moved": 0, "bytes": 0, "errors": errors}

        m = svc.load_manifest()
        batch = svc.new_batch_id(m)
        entry = lambda fs: [{"rel": f["rel"], "size": f["size"],
                             "quality": f"{f['format']} {f['detail']}"} for f in fs]
        m[batch] = {"created": time.time(), "files": entry(plan)}
        svc.save_json(svc.MANIFEST, m)

        moved = []
        for f in plan:
            try:
                svc.move(svc.library_path(f["rel"]), os.path.join(svc.QDIR, batch, f["rel"]))
                f["moved"] = True
                moved.append(f)
            except Exception as e:
                errors.append(f"{f['rel']}: {e}")
        if moved:
            m[batch]["files"] = entry(moved)
        else:
            del m[batch]
        svc.save_json(svc.MANIFEST, m)
    return {"batch": batch if moved else None, "moved": len(moved),
            "bytes": sum(f["size"] for f in moved), "errors": errors}


@router.post("/upgrade")
def upgrade(req: UpgradeReq):
    """Move a better copy into the album in place of its lower-quality copy.
    The replaced copy goes to quarantine and the batch records the move, so
    Restore puts both files back where they were."""
    with svc.MLOCK:
        with svc.LOCK:
            if svc.STATE["status"] != "done":
                raise HTTPException(409, "Run a scan first.")
            hit = next(((r, f) for c in svc.STATE["clusters"] for r in c["rows"]
                        for f in r["files"] if f["rel"] == req.rel), None)
        if not hit or hit[1]["moved"] or not hit[1].get("upgrade"):
            raise HTTPException(400, "That copy can't replace anything. Scan again.")
        row, p = hit
        up = p["upgrade"]
        k = next((f for f in row["files"] if f["rel"] == up["replace"] and not f["moved"]), None)
        if k is None or not svc.unchanged(p) or not svc.unchanged(k):
            raise HTTPException(409, "These files changed since the scan. Scan again.")
        try:
            src, dst = svc.library_path(p["rel"]), svc.library_path(up["to"])
        except ValueError:
            raise HTTPException(400, "That path is outside the library.")
        if up["to"] != k["rel"] and os.path.lexists(dst):
            raise HTTPException(409, f"{up['to']} already exists.")

        m = svc.load_manifest()
        batch = svc.new_batch_id(m)
        m[batch] = {"created": time.time(),
                    "files": [{"rel": k["rel"], "size": k["size"],
                               "quality": f"{k['format']} {k['detail']}"}],
                    "moves": [{"from": p["rel"], "to": up["to"], "size": p["size"],
                               "quality": f"{p['format']} {p['detail']}"}]}
        svc.save_json(svc.MANIFEST, m)
        try:
            svc.move(svc.library_path(k["rel"]), os.path.join(svc.QDIR, batch, k["rel"]))
        except Exception as e:
            del m[batch]
            svc.save_json(svc.MANIFEST, m)
            raise HTTPException(500, f"Couldn't quarantine {k['rel']}: {e}")
        try:
            svc.move(src, dst)
        except Exception as e:  # put the album's copy back; nothing changed
            svc.move(os.path.join(svc.QDIR, batch, k["rel"]), svc.library_path(k["rel"]))
            svc.prune_empty(os.path.join(svc.QDIR, batch))
            del m[batch]
            svc.save_json(svc.MANIFEST, m)
            raise HTTPException(500, f"Couldn't move {p['rel']}: {e}")
        k["moved"] = p["moved"] = True
    return {"batch": batch, "replaced": k["rel"], "now": up["to"]}


@router.get("/quarantine")
def list_quarantine():
    with svc.MLOCK:
        m = svc.load_manifest()
    out = []
    for bid in sorted(m, reverse=True):
        files = [f for f in m[bid]["files"]
                 if os.path.exists(os.path.join(svc.QDIR, bid, f["rel"]))]
        if files:
            out.append({"batch": bid, "created": m[bid]["created"], "files": files,
                        "moves": m[bid].get("moves", []),
                        "bytes": sum(f["size"] for f in files)})
    return out


def _get_batch(m, bid):
    if not svc.BATCH_RE.fullmatch(bid) or bid not in m:
        raise HTTPException(404, "That quarantine batch doesn't exist.")
    return m[bid]


@router.post("/restore")
def restore(req: BatchReq):
    with svc.MLOCK:
        m = svc.load_manifest()
        b = _get_batch(m, req.batch)
        restored, remaining, errors, back = 0, [], [], set()
        moves_left = []
        for mv in b.get("moves", []):
            try:
                here, home = svc.library_path(mv["to"]), svc.library_path(mv["from"])
                if not os.path.lexists(here) or os.path.getsize(here) != mv["size"]:
                    raise FileNotFoundError("it isn't the file we moved anymore")
                svc.move(here, home)
                back.add(mv["from"])
            except Exception as e:
                errors.append(f"{mv['to']}: couldn't move it back to {mv['from']} ({e}).")
                moves_left.append(mv)
        for f in b["files"]:
            src = os.path.join(svc.QDIR, req.batch, f["rel"])
            if not os.path.lexists(src):
                continue
            try:
                svc.move(src, svc.library_path(f["rel"]))
            except FileExistsError:
                errors.append(f"{f['rel']}: a file already exists there, left in quarantine.")
                remaining.append(f)
                continue
            except Exception as e:
                errors.append(f"{f['rel']}: {e}, left in quarantine.")
                remaining.append(f)
                continue
            back.add(f["rel"])
            restored += 1
        bdir = os.path.join(svc.QDIR, req.batch)
        if moves_left:
            b["moves"] = moves_left
        else:
            b.pop("moves", None)
        if remaining:
            b["files"] = remaining
            svc.prune_empty(bdir)
        else:
            del m[req.batch]
            shutil.rmtree(bdir, ignore_errors=True)
        svc.save_json(svc.MANIFEST, m)
    with svc.LOCK:
        for c in svc.STATE["clusters"]:
            for r in c["rows"]:
                for f in r["files"]:
                    if f["rel"] in back:
                        f["moved"] = False
    return {"restored": restored, "errors": errors}


@router.post("/purge")
def purge(req: BatchReq):
    with svc.MLOCK:
        m = svc.load_manifest()
        b = _get_batch(m, req.batch)
        bdir = os.path.join(svc.QDIR, req.batch)
        here = lambda f: os.path.lexists(os.path.join(bdir, f["rel"]))
        freed = sum(f["size"] for f in b["files"] if here(f))
        try:
            if os.path.lexists(bdir):
                shutil.rmtree(bdir)
        except OSError as e:
            left = [f for f in b["files"] if here(f)]
            if left:
                b["files"] = left
            else:
                del m[req.batch]
            svc.save_json(svc.MANIFEST, m)
            raise HTTPException(500, f"Couldn't delete everything in that batch ({e}). "
                                     f"{len(left)} files are still in quarantine.")
        del m[req.batch]
        svc.save_json(svc.MANIFEST, m)
    return {"bytes": freed}
