"""In-process scheduler: replaces the TrueNAS cron jobs for cluster cleanup
and Tidarr tagging. Each module registers its apply() as a job; schedules are
user-editable and persisted under CONFIG_DIR so they survive restarts.
"""
import json
import os
import threading
import traceback

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core import run_history
from app.core.config import CONFIG_DIR, TZ

SCHEDULE_FILE = os.path.join(CONFIG_DIR, "job-schedules.json")

# Defaults matching the old TrueNAS cron jobs this replaces. Everything else
# defaults to disabled until you turn it on from the Scheduler page.
DEFAULT_SCHEDULES = {
    "cluster_cleanup": {"enabled": True, "hour": 3, "minute": 0},
    "tidarr_tagging": {"enabled": True, "hour": 6, "minute": 15},
    # Off by default (new Lidarr/Tidarr imports arrive untagged, so turning
    # this on is an explicit opt-in); 7:00 is after tidarr_tagging's 6:15 -
    # there's no real job-ordering primitive here, just a later clock time.
    "christian_tagging": {"enabled": False, "hour": 7, "minute": 0},
}

_jobs = {}
_scheduler = BackgroundScheduler(timezone=TZ)
_lock = threading.Lock()


def register(job_id, label, run):
    """run() must do the real apply (not a preview) and return a structured
    result dict - the same shape the module's /apply route returns."""
    _jobs[job_id] = {"label": label, "run": run}


def _load_schedules():
    try:
        with open(SCHEDULE_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    merged = {}
    for job_id in _jobs:
        merged[job_id] = dict({"enabled": False, "hour": 3, "minute": 0},
                               **DEFAULT_SCHEDULES.get(job_id, {}))
        if job_id in data:
            merged[job_id].update(data[job_id])
    return merged


def _save_schedules(schedules):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp = SCHEDULE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(schedules, fh, indent=1)
    os.replace(tmp, SCHEDULE_FILE)


def _run_and_record(job_id, trigger):
    job = _jobs[job_id]
    rec = run_history.start(job_id, trigger)
    try:
        result = job["run"]()
        run_history.finish(rec, "ok", result)
    except Exception as e:
        run_history.finish(rec, "error", {"error": str(e)}, error=traceback.format_exc())


def trigger_now(job_id):
    if job_id not in _jobs:
        raise KeyError(job_id)
    threading.Thread(target=_run_and_record, args=(job_id, "manual"), daemon=True).start()


def apply_schedules():
    with _lock:
        for ap_job in list(_scheduler.get_jobs()):
            ap_job.remove()
        for job_id, cfg in _load_schedules().items():
            if not cfg.get("enabled"):
                continue
            _scheduler.add_job(_run_and_record,
                                CronTrigger(hour=cfg.get("hour", 3), minute=cfg.get("minute", 0)),
                                args=(job_id, "scheduled"), id=job_id, replace_existing=True)


def start():
    if not _scheduler.running:
        _scheduler.start()
    apply_schedules()


def set_schedule(job_id, enabled=None, hour=None, minute=None):
    if job_id not in _jobs:
        raise KeyError(job_id)
    schedules = _load_schedules()
    cfg = schedules[job_id]
    if enabled is not None:
        cfg["enabled"] = enabled
    if hour is not None:
        cfg["hour"] = hour
    if minute is not None:
        cfg["minute"] = minute
    _save_schedules(schedules)
    apply_schedules()
    return cfg


def list_jobs():
    schedules = _load_schedules()
    out = []
    for job_id, job in _jobs.items():
        ap_job = _scheduler.get_job(job_id)
        cfg = schedules.get(job_id, {})
        out.append({
            "id": job_id, "label": job["label"], "enabled": cfg.get("enabled", False),
            "hour": cfg.get("hour"), "minute": cfg.get("minute"),
            "next_run": ap_job.next_run_time.isoformat() if ap_job and ap_job.next_run_time else None,
            "last_run": run_history.last(job_id),
        })
    return out
