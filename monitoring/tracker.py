"""Longitudinal health timeline tracker.

Tracks symptom progression, triage history, wearable trends, and
check-in data over time. Provides structured timeline queries.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_STORE_PATH = Path.home() / ".phta" / "health_timeline.json"


class HealthTracker:
    def __init__(self) -> None:
        self._timeline: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if not _STORE_PATH.exists():
            return
        try:
            self._timeline = json.loads(_STORE_PATH.read_text())
        except Exception:
            logger.exception("Failed to load health timeline")

    def _save(self) -> None:
        _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _STORE_PATH.write_text(json.dumps(self._timeline, indent=2))

    def add_entry(self, data: dict[str, Any]) -> str:
        import uuid
        entry = {
            "id": uuid.uuid4().hex[:10],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        self._timeline.append(entry)
        self._save()
        return entry["id"]

    def get_timeline(self, days: int = 30) -> list[dict[str, Any]]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return [
            e for e in self._timeline
            if datetime.fromisoformat(e["timestamp"]) >= cutoff
        ]

    def get_latest(self, entry_type: str | None = None) -> dict[str, Any] | None:
        items = self._timeline
        if entry_type:
            items = [e for e in items if e.get("type") == entry_type]
        return items[-1] if items else None

    def get_symptom_history(self, symptom: str, days: int = 30) -> list[dict]:
        return [
            e for e in self.get_timeline(days)
            if e.get("type") == "symptom" and symptom.lower() in str(e.get("data", "")).lower()
        ]

    def get_triage_history(self, days: int = 90) -> list[dict]:
        return [e for e in self.get_timeline(days) if e.get("type") == "triage"]

    def clear(self) -> None:
        self._timeline = []
        self._save()
