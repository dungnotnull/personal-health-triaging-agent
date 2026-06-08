"""Alert manager — escalation alerts for monitoring plans.

Manages alert thresholds, sends notifications, and tracks alert history.
Integrates with the wearable data pipeline and monitoring scheduler.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ALERTS_PATH = Path.home() / ".phta" / "alerts.json"

_ALERT_THRESHOLDS = {
    "heart_rate_bpm": {"low": 50, "high": 120},
    "spo2_percent": {"low": 94, "critical": 90},
    "temperature_c": {"high": 39.0, "critical": 40.0},
    "sleep_hours_last_night": {"low": 4},
}


class Alert:
    def __init__(self, alert_type: str, severity: str, message: str,
                 data: dict[str, Any] | None = None):
        self.alert_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + alert_type[:4]
        self.alert_type = alert_type
        self.severity = severity
        self.message = message
        self.data = data or {}
        self.created_at = datetime.now(timezone.utc)
        self.acknowledged = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "acknowledged": self.acknowledged,
        }


class AlertManager:
    def __init__(self) -> None:
        self._alerts: list[Alert] = []
        self._load()

    def _load(self) -> None:
        if not _ALERTS_PATH.exists():
            return
        try:
            data = json.loads(_ALERTS_PATH.read_text())
            for a in data:
                alert = Alert(a["alert_type"], a["severity"], a["message"], a.get("data"))
                alert.alert_id = a["alert_id"]
                alert.created_at = datetime.fromisoformat(a["created_at"])
                alert.acknowledged = a.get("acknowledged", False)
                self._alerts.append(alert)
        except Exception:
            pass

    def _save(self) -> None:
        _ALERTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        _ALERTS_PATH.write_text(json.dumps(
            [a.to_dict() for a in self._alerts[-100:]], indent=2
        ))

    def check_thresholds(self, wearable_data: dict[str, Any],
                         plan: dict | None = None) -> list[dict[str, Any]]:
        fired = []
        for metric, thresholds in _ALERT_THRESHOLDS.items():
            value = wearable_data.get(metric)
            if value is None:
                continue
            if "low" in thresholds and value < thresholds["low"]:
                fired.append({
                    "metric": metric, "value": value,
                    "threshold": thresholds["low"],
                    "direction": "below",
                    "severity": "warning",
                })
            if "high" in thresholds and value > thresholds["high"]:
                fired.append({
                    "metric": metric, "value": value,
                    "threshold": thresholds["high"],
                    "direction": "above",
                    "severity": "warning" if value < thresholds.get("critical", float("inf")) else "critical",
                })
            if "critical" in thresholds and value < thresholds["critical"] and metric == "spo2_percent":
                fired.append({
                    "metric": metric, "value": value,
                    "threshold": thresholds["critical"],
                    "direction": "below",
                    "severity": "critical",
                })
        for f in fired:
            self.create_alert(
                f"wearable_{f['metric']}", f["severity"],
                f"{f['metric']} is {f['value']} ({f['direction']} threshold {f['threshold']})",
                f,
            )
        return fired

    def create_alert(self, alert_type: str, severity: str, message: str,
                     data: dict[str, Any] | None = None) -> Alert:
        alert = Alert(alert_type, severity, message, data)
        self._alerts.append(alert)
        self._save()
        return alert

    def send_alert(self, alert: dict) -> bool:
        logger.info(f"ALERT [{alert.get('severity', 'info')}]: {alert.get('message', '')}")
        return True

    def get_alerts(self, severity: str | None = None,
                   acknowledged: bool | None = False) -> list[dict[str, Any]]:
        results = self._alerts
        if severity:
            results = [a for a in results if a.severity == severity]
        if acknowledged is not None:
            results = [a for a in results if a.acknowledged == acknowledged]
        return [a.to_dict() for a in results]

    def acknowledge(self, alert_id: str) -> bool:
        for a in self._alerts:
            if a.alert_id == alert_id:
                a.acknowledged = True
                self._save()
                return True
        return False
