"""Scheduler and run history API: replaces the TrueNAS cron jobs for cluster
cleanup and Tidarr tagging with enable/disable, a schedule editor, and a
drill-down into every past run's full output.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core import run_history, scheduler
from app.core.auth import require_auth

router = APIRouter(prefix="/api/jobs", tags=["scheduler"], dependencies=[Depends(require_auth)])


class ScheduleReq(BaseModel):
    enabled: bool | None = None
    hour: int | None = None
    minute: int | None = None


@router.get("")
def list_jobs():
    return scheduler.list_jobs()


@router.post("/{job_id}/trigger")
def trigger(job_id: str):
    try:
        scheduler.trigger_now(job_id)
    except KeyError:
        raise HTTPException(404, f"No such job: {job_id}")
    return {"ok": True}


@router.put("/{job_id}/schedule")
def set_schedule(job_id: str, req: ScheduleReq):
    try:
        return scheduler.set_schedule(job_id, enabled=req.enabled, hour=req.hour, minute=req.minute)
    except KeyError:
        raise HTTPException(404, f"No such job: {job_id}")


@router.get("/history")
def history(job_id: str | None = None, limit: int = 50):
    return run_history.list_for(job_id=job_id, limit=limit)


@router.get("/history/{run_id}")
def history_detail(run_id: str):
    rec = run_history.get(run_id)
    if rec is None:
        raise HTTPException(404, "No such run.")
    return rec
