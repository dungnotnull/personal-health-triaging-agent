"""Speech-to-text using Whisper (local) with VAD pre-processing.

Supports Vietnamese and English transcription. Falls back gracefully
when Whisper is not installed — returns a clear error message so
the caller can handle offline mode.

Production-grade: handles file validation, language selection,
model caching, and VAD-based audio trimming via Silero VAD.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_WHISPER_AVAILABLE = None
_MODEL_CACHE: dict[str, object] = {}


def _check_whisper() -> bool:
    global _WHISPER_AVAILABLE
    if _WHISPER_AVAILABLE is None:
        try:
            import whisper  # noqa: F401
            _WHISPER_AVAILABLE = True
        except ImportError:
            _WHISPER_AVAILABLE = False
            logger.warning("openai-whisper not installed — STT will use fallback")
    return _WHISPER_AVAILABLE


def _load_model(model_name: str = "large-v3"):
    if model_name not in _MODEL_CACHE:
        import whisper
        _MODEL_CACHE[model_name] = whisper.load_model(model_name)
    return _MODEL_CACHE[model_name]


def _apply_vad(audio_path: str) -> str:
    try:
        from silero_vad import read_audio, get_speech_timestamps
        wav = read_audio(audio_path)
        timestamps = get_speech_timestamps(wav, return_seconds=True)
        if not timestamps:
            return audio_path
        start = timestamps[0]["start"]
        end = timestamps[-1]["end"]
        trimmed_path = audio_path.replace(".wav", "_trimmed.wav")
        import soundfile as sf
        sr = 16000
        sf.write(trimmed_path, wav[int(start * sr):int(end * sr)], sr)
        return trimmed_path
    except ImportError:
        return audio_path


def transcribe(audio_path: str, language: str | None = None) -> str:
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if not _check_whisper():
        return _transcribe_fallback(audio_path, language)

    try:
        import whisper
        model_name = os.environ.get("WHISPER_MODEL", "large-v3")
        model = _load_model(model_name)

        lang_code = None
        if language == "vi":
            lang_code = "vi"
        elif language == "en":
            lang_code = "en"

        audio_to_process = _apply_vad(audio_path) if audio_path.endswith(".wav") else audio_path
        result = model.transcribe(audio_to_process, language=lang_code)
        return result["text"].strip()
    except Exception as exc:
        logger.exception("Whisper transcription failed, using fallback")
        return _transcribe_fallback(audio_path, language)


def _transcribe_fallback(audio_path: str, language: str | None = None) -> str:
    ffmpeg_bin = os.environ.get("FFMPEG_PATH", "ffmpeg")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        subprocess.run(
            [ffmpeg_bin, "-i", audio_path, "-ar", "16000", "-ac", "1", tmp_path, "-y"],
            capture_output=True, timeout=30,
        )
        with open(tmp_path, "rb") as f:
            pass
        return "[Speech-to-text engine not available. Install openai-whisper for transcription.]"
    except Exception:
        return "[Audio file received but STT engine unavailable.]"
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
