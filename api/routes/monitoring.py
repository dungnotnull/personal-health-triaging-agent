"""Monitoring plan management and alert configuration endpoints."""

from fastapi import APIRouter, HTTPException
from monitoring.scheduler import MonitoringScheduler

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

scheduler = MonitoringScheduler()


@router.get("/plans")
async def list_plans():
    return {"plans": scheduler.list_active_plans()}


@router.post("/plans")
async def create_plan(request: dict):
    plan = scheduler.create_plan(
        condition=request.get("condition", "default"),
        triage_level=request.get("triage_level", 3),
    )
    return plan.to_dict()


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str):
    plan = scheduler._plans.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan.to_dict()


@router.post("/plans/{plan_id}/checkin")
async def checkin(plan_id: str, request: dict):
    entry = scheduler.record_checkin(
        plan_id,
        notes=request.get("notes", ""),
        symptoms=request.get("symptoms", ""),
        temperature_c=request.get("temperature_c"),
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Plan not found")
    escalated = scheduler.check_escalation(
        plan_id,
        request.get("symptoms", ""),
        request.get("temperature_c"),
    )
    return {"checkin": entry, "escalation_recommended": escalated}


@router.delete("/plans/{plan_id}")
async def cancel_plan(plan_id: str):
    success = scheduler.cancel_plan(plan_id)
    if not success:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"status": "cancelled", "plan_id": plan_id}
