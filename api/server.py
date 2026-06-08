"""FastAPI server — REST/WebSocket API layer for PHTA.

Provides endpoints for:
  - POST /triage — submit symptoms, get triage recommendation
  - GET /health — health check
  - WebSocket /ws — real-time chat-based triage conversation
  - GET /sessions/{id} — retrieve session state
  - DELETE /sessions/{id} — end session
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from agent.orchestrator import handle_user_input
from agent.session_manager import session_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("phta.api")

VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"PHTA API v{VERSION} starting")
    yield
    logger.info("PHTA API shutting down")


app = FastAPI(
    title="PHTA — Personal Health Triaging Agent",
    version=VERSION,
    description="AI-powered clinical triage screening API. Not a diagnostic tool.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Route Registration ─────────────────────────────────────────────
from api.routes.triage import router as triage_router
from api.routes.wearable import router as wearable_router
from api.routes.monitoring import router as monitoring_router
from api.routes.health_record import router as health_record_router

app.include_router(triage_router)
app.include_router(wearable_router)
app.include_router(monitoring_router)
app.include_router(health_record_router)


# ── REST Endpoints ──────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": VERSION}


@app.post("/triage")
async def triage(request: dict):
    """Submit symptoms for triage evaluation."""
    user_text = request.get("text", "")
    session_id = request.get("session_id")
    wearable = request.get("wearable_data")

    if not user_text and not session_id:
        raise HTTPException(status_code=400, detail="Either 'text' or 'session_id' is required")

    result = handle_user_input(user_text, session_id, wearable)
    return result


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    session = session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    deleted = session_manager.delete(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "session_id": session_id}


# ── WebSocket ───────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_triage(websocket: WebSocket):
    await websocket.accept()
    session_id = None

    try:
        while True:
            data = await websocket.receive_json()
            user_text = data.get("text", "")
            wearable = data.get("wearable_data")

            result = handle_user_input(user_text, session_id, wearable)
            session_id = result.get("session_id")

            await websocket.send_json(result)

            if result.get("is_complete"):
                await websocket.close()
                break
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception:
        logger.exception("WebSocket error")
