"""Symptom intake & structured interview agent.

Drives the clinical interview using the question tree engine and
optionally the LLM for conversational empathy. Collects structured
symptom profiles constrained to max 10 questions per interview.
"""

from __future__ import annotations

from agent.question_engine import QuestionTreeEngine
from agent.session_manager import Session, SessionPhase

MAX_QUESTIONS = 10


def start_interview(session: Session, user_input: str, llm_provider: str = "ollama") -> str:
    session.phase = SessionPhase.STRUCTURED_INTERVIEW
    session.chief_complaint = user_input

    engine = QuestionTreeEngine(user_input)
    first_q = engine.next_question()
    if first_q is None:
        session.phase = SessionPhase.TRIAGE_CLASSIFICATION
        return _wrap_disclaimer("I have enough information. Let me evaluate your situation.")

    qid = first_q.get("id", "")
    session._question_engine = engine
    session.add_answer("_chief_complaint", user_input)

    lang = _guess_language(user_input)
    q_text = first_q.get(f"question_{lang}", first_q.get("question_en", str(first_q)))
    return _wrap_disclaimer(q_text)


def ask_next_question(session: Session) -> str | None:
    engine = getattr(session, "_question_engine", None)
    if engine is None:
        session.phase = SessionPhase.TRIAGE_CLASSIFICATION
        return None

    if session.asked_questions and session.asked_questions[-1] not in session.interview_answers:
        pass

    next_q = engine.next_question()
    if next_q is None or len(session.asked_questions) >= MAX_QUESTIONS:
        session.phase = SessionPhase.TRIAGE_CLASSIFICATION
        return None

    qid = next_q.get("id", "")
    if "red_flag" in next_q:
        session.phase = SessionPhase.COMPLETED
        return None

    session.add_answer(qid, "")
    return next_q.get("question_en", str(next_q))


def extract_symptom_profile(text: str) -> dict:
    from nlp.symptom_extractor import extract_symptoms as nlp_extract
    return nlp_extract(text)


def _guess_language(text: str) -> str:
    from nlp.language_detector import detect_language
    return detect_language(text)


def _wrap_disclaimer(text: str) -> str:
    return f"{text}\n\n⚠️ This is not a medical diagnosis. Always consult a qualified healthcare professional."
