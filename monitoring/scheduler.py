"""Monitoring scheduler — persistent health check-in reminders.

Uses APScheduler for scheduling condition-specific check-ins.
Supports: one-time reminders, recurring check-ins, and escalation triggers.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_STORE_PATH = Path.home() / ".phta" / "monitoring_plans.json"

_CONDITION_SCHEDULES = {
    "fever": {"check_interval_hours": 4, "duration_days": 3, "temp_check": True},
    "headache": {"check_interval_hours": 8, "duration_days": 5, "temp_check": False},
    "respiratory": {"check_interval_hours": 6, "duration_days": 7, "temp_check": False},
    "abdominal_pain": {"check_interval_hours": 4, "duration_days": 3, "temp_check": False},
    "cough": {"check_interval_hours": 8, "duration_days": 7, "temp_check": True},
    "default": {"check_interval_hours": 12, "duration_days": 5, "temp_check": False},
}


class MonitoringPlan:
    def __init__(self, plan_id: str, condition: str, triage_level: int,
                 created_at: datetime | None = None):
        self.plan_id = plan_id
        self.condition = condition
        self.triage_level = triage_level
        self.created_at = created_at or datetime.now(timezone.utc)
        cfg = _CONDITION_SCHEDULES.get(condition, _CONDITION_SCHEDULES["default"])
        self.check_interval_hours = cfg["check_interval_hours"]
        self.duration_days = cfg["duration_days"]
        self.temp_check = cfg["temp_check"]
        self.last_checkin: datetime | None = None
        self.next_checkin = self.created_at + timedelta(hours=self.check_interval_hours)
        self.escalation_triggers: list[str] = []
        self.active = True
        self.checkin_history: list[dict[str, Any]] = []

    def record_checkin(self, notes: str = "", symptoms: str = "",
                       temperature_c: float | None = None) -> dict:
        now = datetime.now(timezone.utc)
        entry = {
            "timestamp": now.isoformat(),
            "notes": notes,
            "symptoms": symptoms,
            "temperature_c": temperature_c,
        }
        self.checkin_history.append(entry)
        self.last_checkin = now
        self.next_checkin = now + timedelta(hours=self.check_interval_hours)
        return entry

    def should_escalate(self, new_symptoms: str, temperature_c: float | None = None) -> bool:
        escalation_keywords = [
            "breathing", "breath", "chest pain", "confusion", "severe",
            "worse", "worsening", "stiff neck", "rash", "blood",
        ]
        if new_symptoms and any(k in new_symptoms.lower() for k in escalation_keywords):
            return True
        if temperature_c and temperature_c >= 39.5:
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "condition": self.condition,
            "triage_level": self.triage_level,
            "created_at": self.created_at.isoformat(),
            "check_interval_hours": self.check_interval_hours,
            "duration_days": self.duration_days,
            "last_checkin": self.last_checkin.isoformat() if self.last_checkin else None,
            "next_checkin": self.next_checkin.isoformat(),
            "escalation_triggers": self.escalation_triggers,
            "active": self.active,
            "checkin_history": self.checkin_history,
        }


class MonitoringScheduler:
    def __init__(self) -> None:
        self._plans: dict[str, MonitoringPlan] = {}
        self._load()

    def _load(self) -> None:
        if not _STORE_PATH.exists():
            return
        try:
            data = json.loads(_STORE_PATH.read_text())
            for plan_data in data:
                plan = MonitoringPlan(
                    plan_id=plan_data["plan_id"],
                    condition=plan_data["condition"],
                    triage_level=plan_data["triage_level"],
                    created_at=datetime.fromisoformat(plan_data["created_at"]),
                )
                plan.check_interval_hours = plan_data.get("check_interval_hours", 12)
                plan.duration_days = plan_data.get("duration_days", 5)
                plan.active = plan_data.get("active", True)
                plan.escalation_triggers = plan_data.get("escalation_triggers", [])
                plan.checkin_history = plan_data.get("checkin_history", [])
                if plan_data.get("last_checkin"):
                    plan.last_checkin = datetime.fromisoformat(plan_data["last_checkin"])
                if plan_data.get("next_checkin"):
                    plan.next_checkin = datetime.fromisoformat(plan_data["next_checkin"])
                self._plans[plan.plan_id] = plan
        except Exception:
            logger.exception("Failed to load monitoring plans")

    def _save(self) -> None:
        _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _STORE_PATH.write_text(json.dumps([p.to_dict() for p in self._plans.values()], indent=2))

    def create_plan(self, condition: str, triage_level: int) -> MonitoringPlan:
        import uuid
        plan_id = uuid.uuid4().hex[:10]
        plan = MonitoringPlan(plan_id, condition, triage_level)
        self._plans[plan_id] = plan
        self._save()
        return plan

    def schedule_checkin(self, plan_id: str, interval_hours: int = 0) -> bool:
        plan = self._plans.get(plan_id)
        if not plan:
            return False
        if interval_hours > 0:
            plan.check_interval_hours = interval_hours
        plan.next_checkin = datetime.now(timezone.utc) + timedelta(hours=plan.check_interval_hours)
        self._save()
        return True

    def get_due_checkins(self) -> list[MonitoringPlan]:
        now = datetime.now(timezone.utc)
        return [p for p in self._plans.values()
                if p.active and p.next_checkin <= now]

    def record_checkin(self, plan_id: str, notes: str = "",
                       symptoms: str = "", temperature_c: float | None = None) -> dict | None:
        plan = self._plans.get(plan_id)
        if not plan:
            return None
        entry = plan.record_checkin(notes, symptoms, temperature_c)
        self._save()
        return entry

    def cancel_plan(self, plan_id: str) -> bool:
        plan = self._plans.get(plan_id)
        if plan:
            plan.active = False
            self._save()
            return True
        return False

    def list_active_plans(self) -> list[dict]:
        return [p.to_dict() for p in self._plans.values() if p.active]

    def check_escalation(self, plan_id: str, new_symptoms: str,
                         temperature_c: float | None = None) -> bool:
        plan = self._plans.get(plan_id)
        if not plan:
            return False
        return plan.should_escalate(new_symptoms, temperature_c)
