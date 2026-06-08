"""Encrypted health record CRUD, consent management, data export."""

from fastapi import APIRouter, HTTPException
from monitoring.tracker import HealthTracker

router = APIRouter(prefix="/health-record", tags=["health_record"])

tracker = HealthTracker()


@router.get("/timeline")
async def get_timeline(days: int = 30):
    return {"timeline": tracker.get_timeline(days)}


@router.post("/entries")
async def add_entry(request: dict):
    entry_id = tracker.add_entry({
        "type": request.get("type", "note"),
        "data": request.get("data", {}),
        "tags": request.get("tags", []),
    })
    return {"id": entry_id, "status": "stored"}


@router.get("/latest")
async def latest_entry(entry_type: str = None):
    entry = tracker.get_latest(entry_type)
    if not entry:
        raise HTTPException(status_code=404, detail="No entries found")
    return entry


@router.get("/triage-history")
async def triage_history(days: int = 90):
    return {"history": tracker.get_triage_history(days)}


@router.delete("/all")
async def delete_all_data():
    tracker.clear()
    return {"status": "deleted", "message": "All health data removed"}
