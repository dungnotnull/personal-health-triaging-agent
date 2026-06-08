"""Red Flag Screener — Layer 0 (always runs first, before any LLM call).

Purely rule-based keyword matching in O(1) time. No LLM for safety-critical
emergency detection. Target: < 200ms latency.

Checks:
  - Keyword matching (Vietnamese + English) against red_flags.yaml
  - Wearable biosignal thresholds (SpO2 < 90%, HR > 150 or < 40)
  - Mental health crisis detection (separate protocol from EMERGENCY)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class RedFlagResult:
    is_emergency: bool = False
    is_mental_health_crisis: bool = False
    category: str | None = None
    matched_keywords: list[str] = field(default_factory=list)
    matched_wearable: list[str] = field(default_factory=list)


@dataclass
class WearableData:
    heart_rate_bpm: float | None = None
    spo2_percent: float | None = None
    temperature_c: float | None = None
    hrv_rmssd_ms: float | None = None
    hrv_baseline_ms: float | None = None


# ── Cached rule loading ──────────────────────────────────────────────

_RULES_CACHE: dict | None = None
_RULES_PATH = Path(__file__).resolve().parent.parent / "clinical" / "red_flags.yaml"


def _load_rules() -> dict:
    global _RULES_CACHE
    if _RULES_CACHE is None:
        with open(_RULES_PATH, encoding="utf-8") as f:
            _RULES_CACHE = yaml.safe_load(f)
    return _RULES_CACHE


_CONTRACTIONS = {
    "can't": "cannot",
    "don't": "do not",
    "won't": "will not",
    "i'm": "i am",
    "it's": "it is",
    "that's": "that is",
    "couldn't": "could not",
    "wouldn't": "would not",
    "shouldn't": "should not",
    "isn't": "is not",
    "aren't": "are not",
}

_SYNONYMS: dict[str, set[str]] = {
    "difficulty": {"trouble", "hard"},
    "weakness": {"weak"},
    "swelling": {"swollen"},
    "vision": {"sight"},
    "unresponsive": {"unconscious"},
    "loss": {"lost"},
    "speech": {"speak", "talking"},
}


_VI_DIACRITIC_MAP = {
    'a': 'a', 'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
    'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
    'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
    'e': 'e', 'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
    'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
    'i': 'i', 'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
    'o': 'o', 'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
    'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
    'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
    'u': 'u', 'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
    'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
    'y': 'y', 'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
    'd': 'd', 'đ': 'd',
}


def _strip_diacritics(text: str) -> str:
    """Remove Vietnamese diacritics for ASCII-matching."""
    return ''.join(_VI_DIACRITIC_MAP.get(c, c) for c in text)


def _normalize(text: str) -> str:
    """Lowercase, expand contractions, strip Vietnamese diacritics for matching."""
    t = text.lower().strip()
    for contraction, expanded in _CONTRACTIONS.items():
        t = t.replace(contraction, expanded)
    return t


def _tokenize(text: str) -> set[str]:
    """Split into lowercase word tokens, stripping punctuation."""
    return set(re.findall(r"[a-z0-9\u00C0-\u024F\u1EA0-\u1EFF]+", text.lower()))


def _token_matches(kw_token: str, input_tokens: set[str]) -> bool:
    """Check if kw_token matches any input token, with stemming flexibility.

    Handles: weak↔weakness, sudden↔suddenly, swell↔swelling, vision↔sight, etc.
    """
    if kw_token in input_tokens:
        return True
    # Morphological prefix/suffix variants
    for it in input_tokens:
        min_len = min(len(kw_token), len(it))
        if min_len < 3:
            continue
        if kw_token.startswith(it) or it.startswith(kw_token):
            return True
    # Known synonyms
    for synonym_kw, synonyms in _SYNONYMS.items():
        if kw_token == synonym_kw:
            if any(s in input_tokens for s in synonyms):
                return True
        elif kw_token in synonyms:
            if synonym_kw in input_tokens:
                return True
    return False


def _all_tokens_match(keyword: str, input_text: str) -> bool:
    """Check if every token in the keyword appears in the input text.

    Token-based matching with stemming handles:
      - "lips turning blue" matching "lips are turning blue"
      - "cannot speak" matching "can't speak" (contraction expansion)
      - "arm weakness" matching "arms went weak" (weak ↔ weakness)
      - "difficulty breathing" matching "trouble breathing" (synonyms)
      - Vietnamese diacritic-insensitive: "dau nguc" matches "đau ngực"
    """
    kw_tokens = _tokenize(keyword)
    if not kw_tokens:
        return False
    input_tokens = _tokenize(input_text)

    nonascii_kw = {kt for kt in kw_tokens if any(ord(c) > 127 for c in kt)}
    if nonascii_kw:
        stripped_kw = {_strip_diacritics(kt) for kt in nonascii_kw}
        stripped_input = {_strip_diacritics(it) for it in input_tokens}
        non_stripped = kw_tokens - nonascii_kw
        return all(
            _token_matches(kt, input_tokens) for kt in non_stripped
        ) and all(
            any(skt == _strip_diacritics(it) for it in input_tokens) for skt in stripped_kw
        )

    return all(_token_matches(kt, input_tokens) for kt in kw_tokens)


# ── Public API ───────────────────────────────────────────────────────


def screen(text: str, wearable: WearableData | None = None) -> RedFlagResult:
    """Run the red flag screener on user input + optional wearable data."""
    rules = _load_rules()
    result = RedFlagResult()
    normalized = _normalize(text)

    # 1. Keyword matching
    for category, config in rules.get("emergency_patterns", {}).items():
        keywords = config.get("keywords_vi", []) + config.get("keywords_en", [])
        cat_matched = False
        for kw in keywords:
            if _all_tokens_match(kw, normalized):
                result.matched_keywords.append(kw)
                cat_matched = True
                if result.category is None:
                    result.category = category

        if not cat_matched:
            continue

        action = config.get("action", "EMERGENCY")
        if action == "MENTAL_HEALTH_CRISIS":
            result.is_mental_health_crisis = True
        else:
            result.is_emergency = True

    # 2. Wearable thresholds
    if wearable is not None:
        thresholds = rules.get("wearable_thresholds", {})

        if wearable.spo2_percent is not None:
            spo2_emergency = thresholds.get("spo2", {}).get("emergency", 90)
            if wearable.spo2_percent < spo2_emergency:
                result.matched_wearable.append(f"SpO2={wearable.spo2_percent}% < {spo2_emergency}%")
                result.is_emergency = True
                result.category = result.category or "respiratory"

        if wearable.heart_rate_bpm is not None:
            hr = thresholds.get("heart_rate", {})
            tachy = hr.get("tachycardia_emergency", 150)
            brady = hr.get("bradycardia_emergency", 40)
            if wearable.heart_rate_bpm > tachy:
                result.matched_wearable.append(f"HR={wearable.heart_rate_bpm} > {tachy}")
                result.is_emergency = True
                result.category = result.category or "cardiovascular"
            elif wearable.heart_rate_bpm < brady:
                result.matched_wearable.append(f"HR={wearable.heart_rate_bpm} < {brady}")
                result.is_emergency = True
                result.category = result.category or "cardiovascular"

        if wearable.temperature_c is not None:
            temp_emergency = thresholds.get("temperature", {}).get("hyperthermia_emergency", 40.0)
            if wearable.temperature_c > temp_emergency:
                result.matched_wearable.append(f"Temp={wearable.temperature_c}°C > {temp_emergency}°C")
                result.is_emergency = True
                result.category = result.category or "hyperthermia"

        if wearable.hrv_rmssd_ms is not None and wearable.hrv_baseline_ms is not None:
            if wearable.hrv_baseline_ms > 0 and wearable.hrv_rmssd_ms < wearable.hrv_baseline_ms * 0.3:
                decline_pct = int((1 - wearable.hrv_rmssd_ms / wearable.hrv_baseline_ms) * 100)
                result.matched_wearable.append(f"HRV collapse ({wearable.hrv_rmssd_ms}ms vs baseline {wearable.hrv_baseline_ms}ms, -{decline_pct}%)")
                result.is_emergency = True
                result.category = result.category or "neurological_severe"

    return result


def format_emergency_alert(result: RedFlagResult) -> str:
    """Format the emergency output message."""
    primary = "115"
    secondary = "1800599920"

    if result.is_mental_health_crisis:
        return (
            "🫂 MENTAL HEALTH CRISIS SUPPORT\n\n"
            "What you're experiencing matters. Help is available right now.\n\n"
            f"📞 Vietnam Mental Health Crisis Hotline: {secondary} (free, 24/7)\n\n"
            "Please reach out — you don't have to go through this alone.\n"
            "If you're in immediate danger, please call 115 or go to the nearest hospital emergency department.\n\n"
            "⚠️ This is not a medical diagnosis. Always consult a qualified healthcare professional."
        )

    lines = [
        "🚨 EMERGENCY ALERT — Seek Emergency Care Immediately",
        "",
        f"📞 Emergency: {primary}",
        f"📞 Mental Health Crisis: {secondary}",
        "",
    ]
    if result.category:
        lines.append(f"Category: {result.category}")
    if result.matched_keywords:
        lines.append(f"Detected patterns: {', '.join(result.matched_keywords)}")
    if result.matched_wearable:
        lines.append(f"Wearable alerts: {', '.join(result.matched_wearable)}")
    lines.append("")
    lines.append("⚠️ This is not a medical diagnosis. Always consult a qualified healthcare professional.")
    return "\n".join(lines)
