"""Text-to-speech using Edge TTS (online, free) with Coqui XTTS fallback.

Supports Vietnamese and English voices. Zero-cost TTS for production.
Graceful fallback when offline or dependencies missing.
"""

from __future__ import annotations

import io
import logging
import os
import tempfile

logger = logging.getLogger(__name__)

_VOICES = {
    "vi": "vi-VN-HoaiMyNeural",
    "en": "en-US-AriaNeural",
}


async def speak(text: str, language: str = "vi") -> bytes | None:
    provider = os.environ.get("TTS_PROVIDER", "edge_tts")
    if provider == "edge_tts":
        return await _edge_tts(text, language)
    elif provider == "coqui":
        return await _coqui_tts(text, language)
    return None


async def _edge_tts(text: str, language: str) -> bytes | None:
    try:
        import edge_tts
        voice = _VOICES.get(language, "en-US-AriaNeural")
        communicate = edge_tts.Communicate(text, voice)
        buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])
        return buffer.getvalue() if buffer.tell() > 0 else None
    except ImportError:
        logger.warning("edge-tts not installed")
    except Exception:
        logger.exception("Edge TTS failed")
    return None


async def _coqui_tts(text: str, language: str) -> bytes | None:
    try:
        import torch
        from TTS.api import TTS
        model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
        tts = TTS(model_name=model_name)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        lang = "vi" if language == "vi" else "en"
        tts.tts_to_file(text=text, speaker_wav=None, language=lang, file_path=tmp_path)
        with open(tmp_path, "rb") as f:
            data = f.read()
        os.unlink(tmp_path)
        return data
    except ImportError:
        logger.warning("Coqui TTS not installed")
    except Exception:
        logger.exception("Coqui TTS failed")
    return None
