"""Main agent orchestration loop — production ready.

Coordinates the PHTA conversation flow:
  1. Red flag screener (always first, no LLM)
  2. Structured clinical interview (question tree engine)
  3. Triage classification (ML + rules)
  4. Monitoring plan generation (levels 3-4)
  5. Output: emergency alert or monitoring plan
"""

from __future__ import annotations

import logging

from agent.intake import ask_next_question, extract_symptom_profile, start_interview
from agent.red_flag_screener import (
    RedFlagResult,
    WearableData,
    format_emergency_alert,
    screen,
)
from agent.session_manager import Session, SessionPhase, session_manager
from agent.triage_classifier import TriageResult, classify

logger = logging.getLogger(__name__)

DISCLAIMER = "⚠️ This is not a medical diagnosis. Always consult a qualified healthcare professional."

TRIAGE_NAMES = {1: "EMERGENCY", 2: "URGENT", 3: "SEMI-URGENT", 4: "NON-URGENT"}
TRIAGE_COLORS = {1: "🔴 RED", 2: "🟠 ORANGE", 3: "🟡 YELLOW", 4: "🟢 GREEN"}
TRIAGE_ACTIONS = {
    1: "Call 115 or go to the nearest ER immediately",
    2: "Go to urgent care or clinic today",
    3: "Book an appointment this week",
    4: "Monitor at home, follow up in 7+ days if not resolved",
}


def _generate_monitoring_plan(session: Session, triage: TriageResult) -> str:
    plan_lines = [
        f"**Triage Assessment: {TRIAGE_COLORS.get(triage.triage_level, '')} {TRIAGE_NAMES.get(triage.triage_level, 'UNKNOWN')}**",
        "",
        f"**Action:** {TRIAGE_ACTIONS.get(triage.triage_level, '')}",
        "",
        f"**What we found:** {triage.primary_concern}",
    ]

    if triage.specialty_routing:
        plan_lines.append(f"**Recommended specialist:** {triage.specialty_routing.replace('_', ' ').title()}")

    plan_lines.append(f"**Confidence:** {triage.confidence:.0%}")

    if triage.escalation_reason:
        plan_lines.append(f"**Why:** {triage.escalation_reason}")

    plan_lines.append("")
    plan_lines.append("**Home Care Guidance:**")

    chief = (session.chief_complaint or "").lower()
    if "fever" in chief or "sốt" in chief:
        plan_lines.append("• Stay hydrated — drink at least 2.5L water per day")
        plan_lines.append("• Monitor temperature every 4 hours")
        plan_lines.append("• Rest as much as possible")
        plan_lines.append("• Seek care immediately if temperature exceeds 39.5°C, stiff neck develops, or breathing becomes difficult")
    elif "headache" in chief or "đau đầu" in chief:
        plan_lines.append("• Rest in a quiet, dark room")
        plan_lines.append("• Stay hydrated")
        plan_lines.append("• Avoid screens and bright light")
        plan_lines.append("• Seek care if headache becomes severe, you develop stiff neck, fever, or vision changes")
    elif "cough" in chief or "ho" in chief:
        plan_lines.append("• Stay hydrated with warm fluids")
        plan_lines.append("• Use honey (if over 1 year old) for cough relief")
        plan_lines.append("• Avoid smoke and irritants")
        plan_lines.append("• Seek care if you develop difficulty breathing, chest pain, or cough up blood")
    elif "abdominal" in chief or "đau bụng" in chief:
        plan_lines.append("• Eat light, easily digestible foods (congee, soup)")
        plan_lines.append("• Avoid fatty, spicy, and fried foods")
        plan_lines.append("• Stay hydrated")
        plan_lines.append("• Seek care immediately if pain becomes severe, you develop rigid abdomen, or vomit blood")
    else:
        plan_lines.append("• Rest and monitor your symptoms")
        plan_lines.append("• Stay hydrated and eat nutritious food")
        plan_lines.append("• Keep track of any new or worsening symptoms")
        plan_lines.append("• Seek care if symptoms worsen or new concerning symptoms appear")

    plan_lines.append("")
    plan_lines.append("**Escalation triggers — seek medical care if:**")
    plan_lines.append("• Symptoms significantly worsen")
    plan_lines.append("• You develop new symptoms (chest pain, difficulty breathing, confusion)")
    plan_lines.append("• Symptoms persist beyond the expected recovery timeline")
    plan_lines.append("")
    plan_lines.append(DISCLAIMER)

    return "\n".join(plan_lines)


def _build_profile_dict(session: Session) -> dict:
    return {
        "chief_complaint": session.chief_complaint or "",
        "symptoms": session.symptoms,
        "answers": session.interview_answers,
        "severity": session.interview_answers.get("severity", ""),
        "pain_scale": session.interview_answers.get("pain_scale"),
        "onset": session.interview_answers.get("onset", ""),
        "duration_hours": session.interview_answers.get("duration_hours"),
        "body_locations": session.interview_answers.get("body_locations", []),
        "medical_history": session.interview_answers.get("medical_history", []),
        "medications": session.interview_answers.get("medications", []),
    }


def _parse_wearable_raw(raw: dict | None):
    if raw is None:
        return WearableData(), raw
    return WearableData(
        heart_rate_bpm=raw.get("heart_rate_bpm"),
        spo2_percent=raw.get("spo2_percent"),
        temperature_c=raw.get("temperature_c"),
    ), raw


def handle_user_input(
    user_text: str,
    session_id: str | None = None,
    wearable_raw: dict | None = None,
) -> dict:
    session = session_manager.get_or_create(session_id) if session_id else session_manager.create()

    # ── STEP 0: Red Flag Screen ──────────────────────────────────
    if session.phase == SessionPhase.RED_FLAG_SCREEN:
        wearable, wearable_dict = _parse_wearable_raw(wearable_raw)
        session.wearable_data = wearable_dict

        result = screen(user_text, wearable)
        session.red_flag_triggered = result.is_emergency or result.is_mental_health_crisis
        session.red_flag_category = result.category
        session.is_mental_health_crisis = result.is_mental_health_crisis

        if result.is_emergency or result.is_mental_health_crisis:
            session.phase = SessionPhase.COMPLETED
            alert = format_emergency_alert(result)
            return {
                "message": alert,
                "triage_level": 1,
                "session_id": session.session_id,
                "is_complete": True,
                "is_emergency": True,
            }

        profile = extract_symptom_profile(user_text)
        session.chief_complaint = profile.get("chief_complaint", user_text)
        session.symptoms = profile.get("symptoms", [])
        for key in ("severity", "pain_scale", "onset", "duration_hours",
                     "body_locations", "medical_history", "medications"):
            if key in profile:
                session.interview_answers[key] = profile[key]

        greeting = start_interview(session, user_text)
        return {
            "message": greeting,
            "triage_level": None,
            "session_id": session.session_id,
            "is_complete": False,
            "is_emergency": False,
        }

    # ── STEP 1: Structured Interview ─────────────────────────────
    if session.phase == SessionPhase.STRUCTURED_INTERVIEW:
        if session.asked_questions:
            last_q = session.asked_questions[-1] if session.asked_questions else None
            if last_q and last_q not in session.interview_answers:
                session.add_answer(f"_{last_q}_text", user_text)

        profile = extract_symptom_profile(user_text)
        for key in ("severity", "pain_scale", "onset", "duration_hours",
                     "body_locations", "medical_history", "medications"):
            val = profile.get(key)
            if val:
                session.interview_answers[key] = val

        next_q = ask_next_question(session)
        if next_q:
            session.add_answer(f"_asked_q_{len(session.asked_questions)}", user_text)
            return {
                "message": next_q,
                "triage_level": None,
                "session_id": session.session_id,
                "is_complete": False,
                "is_emergency": False,
            }

        session.phase = SessionPhase.TRIAGE_CLASSIFICATION

    # ── STEP 2: Triage Classification ────────────────────────────
    if session.phase == SessionPhase.TRIAGE_CLASSIFICATION:
        profile = _build_profile_dict(session)
        triage = classify(profile, session.wearable_data)
        session.set_triage(triage.triage_level, triage.confidence, triage.primary_concern)

        if triage.triage_level <= 2:
            message = (
                f"**Triage Assessment: {TRIAGE_COLORS.get(triage.triage_level)} {TRIAGE_NAMES.get(triage.triage_level)}**\n\n"
                f"**What we found:** {triage.primary_concern}\n\n"
                f"**Action:** {TRIAGE_ACTIONS.get(triage.triage_level)}\n\n"
                f"**Confidence:** {triage.confidence:.0%}\n\n"
                f"{DISCLAIMER}"
            )
        else:
            session.phase = SessionPhase.MONITORING_PLAN
            message = _generate_monitoring_plan(session, triage)

        return {
            "message": message,
            "triage_level": triage.triage_level,
            "session_id": session.session_id,
            "is_complete": True,
            "is_emergency": triage.triage_level == 1,
            "triage_detail": triage.to_dict(),
        }

    # ── STEP 3: Monitoring Plan ──────────────────────────────────
    if session.phase == SessionPhase.MONITORING_PLAN:
        return {
            "message": _generate_monitoring_plan(session, classify(_build_profile_dict(session), session.wearable_data)),
            "triage_level": session.triage_level,
            "session_id": session.session_id,
            "is_complete": True,
            "is_emergency": False,
        }

    return {
        "message": f"Your session has completed. Start a new conversation if you need help. {DISCLAIMER}",
        "triage_level": None,
        "session_id": session.session_id,
        "is_complete": True,
        "is_emergency": False,
    }


def main() -> None:
    import sys

    print("    Personal Health Triaging Agent (PHTA) v1.0.0")
    print("    ⚠️  This is NOT a medical diagnosis.")
    print("    Always consult a qualified healthcare provider.")
    print()
    print("Describe your symptoms (or type 'quit' to exit):")
    print()

    sid = None
    turn = 0
    while True:
        try:
            user_input = input(f"[{turn+1}] You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye. Take care.")
            break

        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye. Take care.")
            break
        if not user_input:
            continue

        response = handle_user_input(user_input, sid)
        sid = response["session_id"]
        print(f"\nPHTA: {response['message']}\n")

        if response.get("is_complete"):
            break
        turn += 1


if __name__ == "__main__":
    main()
