"""Centralised configuration for PHTA.

Loads from environment variables (via .env) and provides typed access
to all settings: LLM provider, emergency contacts, storage paths, etc.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── LLM ──────────────────────────────────────────────────────
    llm_provider: str = "ollama"
    anthropic_api_key: str = ""
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # ── STT / TTS ───────────────────────────────────────────────
    whisper_model: str = "large-v3"
    tts_provider: str = "edge_tts"
    tts_voice_vi: str = "vi-VN-HoaiMyNeural"
    tts_voice_en: str = "en-US-AriaNeural"

    # ── Wearable ─────────────────────────────────────────────────
    apple_health_enabled: bool = False
    google_health_client_id: str = ""
    fitbit_client_id: str = ""
    fitbit_client_secret: str = ""
    garmin_client_id: str = ""

    # ── Storage ──────────────────────────────────────────────────
    health_db_path: str = str(Path.home() / ".phta" / "health.db")
    health_db_encryption_key: str = ""
    session_ttl_hours: int = 24

    # ── Knowledge Crawler ────────────────────────────────────────
    pubmed_api_key: str = ""
    knowledge_crawl_schedule: str = "0 2 * * 0"

    # ── Emergency ────────────────────────────────────────────────
    emergency_number_primary: str = "115"
    emergency_number_secondary: str = "1800599920"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


# ── Triage Level Constants ─────────────────────────────────────────

TRIAGE_LEVELS = {
    1: {"color": "🔴 RED", "name": "EMERGENCY", "action": "Call 115 / go to ER immediately"},
    2: {"color": "🟠 ORANGE", "name": "URGENT", "action": "Go to urgent care / clinic today"},
    3: {"color": "🟡 YELLOW", "name": "SEMI-URGENT", "action": "Book appointment this week"},
    4: {"color": "🟢 GREEN", "name": "NON-URGENT", "action": "Monitor at home, follow-up in 7+ days"},
}

# ── Medical Disclaimer Text (injected into every triage response) ──

MEDICAL_DISCLAIMER = (
    "⚠️ This is not a medical diagnosis. "
    "Always consult a qualified healthcare professional. "
    "If this is a medical emergency, call {emergency_primary} immediately."
)

# ── Emergency Alert Template ───────────────────────────────────────

EMERGENCY_ALERT_TEMPLATE = """🚨 EMERGENCY ALERT — {category}

This triage agent has detected symptoms that may indicate a life-threatening condition.

DO NOT WAIT — SEEK EMERGENCY CARE IMMEDIATELY.

📞 Emergency: {emergency_primary}
📞 Mental Health Crisis: {emergency_secondary}

Detected: {detected_patterns}
Wearable data (if available): {wearable_summary}

{disclaimer}
"""

MENTAL_HEALTH_CRISIS_TEMPLATE = """🫂 MENTAL HEALTH CRISIS SUPPORT

What you're experiencing matters. Help is available right now.

📞 Vietnam Mental Health Crisis Hotline: 1800 599 920 (free, 24/7)

Please reach out — you don't have to go through this alone.
If you're in immediate danger, please call 115 or go to the nearest hospital emergency department.

{disclaimer}
"""
