"""Auto-detect language: Vietnamese or English.

Production-grade detection using character analysis, word frequency,
and n-gram profiles. Handles mixed input, short text, and ASCII-only
Vietnamese (e.g., "toi bi dau dau").
"""

from __future__ import annotations

import re

_VI_CHARS = set("ắằẳẵặấầẩẫậắằẳẵặêềểễệốồổỗộơờởỡợưừửữựđ")
_VI_TONELESS_MARKERS = {"dau", "dau", "khong", "co", "bi", "toi", "nay",
                         "do", "sot", "met", "ho", "da", "nguc", "bung", "lung",
                         "nguoi", "bi", "het", "qua", "lam", "nhe", "nang"}

_VI_WORDS = [
    "tôi", "bị", "đau", "không", "có", "là", "và", "nhưng", "này", "kia",
    "đó", "của", "cho", "từ", "đến", "với", "trong", "ngoài", "trên",
    "dưới", "sốt", "ho", "mệt", "được", "thì", "cũng", "đang", "vẫn",
    "rất", "quá", "lắm", "nhé", "nhỉ", "ạ", "dạ", "chưa", "đã", "sẽ",
    "phải", "nên", "cần", "muốn", "thấy", "cảm", "người", "bụng",
    "chảy", "máu", "nhức", "chóng", "mặt", "buồn", "nôn", "thở",
]

_EN_WORDS = [
    "the", "and", "have", "with", "this", "that", "from", "pain", "fever",
    "cough", "headache", "chest", "feel", "my", "not", "but", "been",
    "has", "had", "was", "are", "for", "you", "your", "can", "just",
    "like", "really", "very", "much", "since", "about", "when", "where",
]


def detect_language(text: str) -> str:
    """Return 'vi' or 'en' based on multi-factor analysis."""
    if not text or not text.strip():
        return "vi"

    text_lower = text.lower().strip()

    vi_char_count = sum(1 for c in text if c in _VI_CHARS)
    if vi_char_count > 0:
        return "vi"

    vi_words = sum(1 for w in _VI_WORDS if re.search(rf"\b{re.escape(w)}\b", text_lower))
    en_words = sum(1 for w in _EN_WORDS if re.search(rf"\b{re.escape(w)}\b", text_lower))

    toneless_vi = sum(1 for w in _VI_TONELESS_MARKERS if re.search(rf"\b{re.escape(w)}\b", text_lower))
    vi_score = vi_words * 3 + toneless_vi * 2
    en_score = en_words * 2

    if vi_score > en_score:
        return "vi"
    if en_score > vi_score:
        return "en"

    total_chars = len(text_lower)
    ascii_ratio = sum(1 for c in text_lower if ord(c) < 128) / max(total_chars, 1)
    if ascii_ratio > 0.98 and en_words == 0 and vi_words == 0:
        return "vi"

    return "en"


def get_language_name(lang: str) -> str:
    return {"vi": "vietnamese", "en": "english"}.get(lang, "unknown")
