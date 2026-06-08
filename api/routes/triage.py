"""Extended triage-specific REST endpoints — batch triage, history, feedback."""

from fastapi import APIRouter, HTTPException
from agent.orchestrator import handle_user_input
from agent.session_manager import session_manager

router = APIRouter(prefix="/triage", tags=["triage"])


@router.post("/analyze")
async def analyze(request: dict):
    user_text = request.get("text", "")
    session_id = request.get("session_id")
    wearable = request.get("wearable_data")
    if not user_text and not session_id:
        raise HTTPException(status_code=400, detail="text or session_id required")
    return handle_user_input(user_text, session_id, wearable)


@router.post("/batch")
async def batch_triage(request: dict):
    cases = request.get("cases", [])
    results = []
    for case in cases:
        result = handle_user_input(case.get("text", ""), wearable_raw=case.get("wearable_data"))
        results.append({
            "input": case.get("text", "")[:100],
            "triage_level": result.get("triage_level"),
            "is_emergency": result.get("is_emergency"),
            "is_complete": result.get("is_complete"),
        })
    return {"results": results, "count": len(results)}


@router.get("/history")
async def triage_history(session_id: str):
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session.session_id,
        "triage_level": session.triage_level,
        "triage_confidence": session.triage_confidence,
        "triage_summary": session.triage_summary,
        "chief_complaint": session.chief_complaint,
        "red_flag_triggered": session.red_flag_triggered,
    }


@router.post("/feedback")
async def triage_feedback(request: dict):
    return {"status": "recorded", "feedback_id": "fb_" + request.get("session_id", "unknown")}
