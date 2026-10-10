"""Run history for the scheduler: every manual and scheduled run of every job,
persisted under CONFIG_DIR so it survives restarts. Capped so it can't grow
without bound.
"""
import json
import os
import threading
import time
import uuid

from app.core.config import CONFIG_DIR

HISTORY_FILE = os.path.join(CONFIG_DIR, "run-history.json")
MAX_RECORDS = 200
_lock = threading.Lock()


def _load():
    try:
        with open(HISTORY_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save(records):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp = HISTORY_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(records[:MAX_RECORDS], fh, indent=1)
    os.replace(tmp, HISTORY_FILE)


def start(job_id, trigger):
    rec = {"id": uuid.uuid4().hex, "job_id": job_id, "trigger": trigger,
           "started": time.time(), "finished": None, "status": "running",
           "result": None, "error": None}
    with _lock:
        records = _load()
        records.insert(0, rec)
        _save(records)
    return rec


def finish(rec, status, result, error=None):
    rec = dict(rec, finished=time.time(), status=status, result=result, error=error)
    with _lock:
        records = _load()
        for i, r in enumerate(records):
            if r["id"] == rec["id"]:
                records[i] = rec
                break
        else:
            records.insert(0, rec)
        _save(records)
    return rec


def last(job_id):
    return next((r for r in _load() if r["job_id"] == job_id), None)


def get(run_id):
    return next((r for r in _load() if r["id"] == run_id), None)


def list_for(job_id=None, limit=50):
    records = _load()
    if job_id:
        records = [r for r in records if r["job_id"] == job_id]
    return records[:limit]
