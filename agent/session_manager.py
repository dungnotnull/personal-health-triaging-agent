"""Session state management for PHTA conversations.

Manages conversation state across turns: tracks which questions have been
asked, stores collected symptom data, and maintains the interview flow.
Sessions are ephemeral (in-memory) by default, with optional encrypted
persistence.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class SessionPhase(Enum):
    RED_FLAG_SCREEN = "red_flag_screen"
    WEARABLE_PULL = "wearable_pull"
    STRUCTURED_INTERVIEW = "structured_interview"
    TRIAGE_CLASSIFICATION = "triage_classification"
    MONITORING_PLAN = "monitoring_plan"
    COMPLETED = "completed"


@dataclass
class Session:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    phase: SessionPhase = SessionPhase.RED_FLAG_SCREEN
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Collected data
    chief_complaint: str | None = None
    symptoms: list[dict[str, Any]] = field(default_factory=list)
    wearable_data: dict[str, Any] | None = None
    interview_answers: dict[str, Any] = field(default_factory=dict)
    asked_questions: list[str] = field(default_factory=list)

    # Triage result
    triage_level: int | None = None
    triage_confidence: float | None = None
    triage_summary: str | None = None

    # Red flag result
    red_flag_triggered: bool = False
    red_flag_category: str | None = None
    is_mental_health_crisis: bool = False

    def add_symptom(self, symptom: dict[str, Any]) -> None:
        self.symptoms.append(symptom)

    def add_answer(self, question_id: str, answer: Any) -> None:
        self.interview_answers[question_id] = answer
        self.asked_questions.append(question_id)

    def set_triage(self, level: int, confidence: float, summary: str) -> None:
        self.triage_level = level
        self.triage_confidence = confidence
        self.triage_summary = summary
        self.phase = SessionPhase.COMPLETED

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "phase": self.phase.value,
            "created_at": self.created_at.isoformat(),
            "chief_complaint": self.chief_complaint,
            "symptoms_count": len(self.symptoms),
            "triage_level": self.triage_level,
            "triage_confidence": self.triage_confidence,
            "triage_summary": self.triage_summary,
            "red_flag_triggered": self.red_flag_triggered,
        }


class SessionManager:
    """In-memory session store with optional encrypted persistence."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self) -> Session:
        session = Session()
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def get_or_create(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            session = Session(session_id=session_id)
            self._sessions[session_id] = session
        return self._sessions[session_id]

    def delete(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def cleanup_expired(self, ttl_hours: int = 24) -> int:
        now = datetime.now(timezone.utc)
        expired = [
            sid
            for sid, s in self._sessions.items()
            if (now - s.created_at).total_seconds() > ttl_hours * 3600
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)


# Global session manager instance
session_manager = SessionManager()
