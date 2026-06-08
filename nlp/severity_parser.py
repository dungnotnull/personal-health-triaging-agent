"""Severity parser — extract severity, duration, quality descriptors.

Handles Vietnamese + English descriptors with numeric scale extraction,
duration parsing, onset detection, and trend analysis. Zero external
model dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class SeverityInfo:
    level: str | None = None
    pain_scale: int | None = None
    duration_hours: float | None = None
    onset: str | None = None
    trend: str | None = None

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "pain_scale": self.pain_scale,
            "duration_hours": self.duration_hours,
            "onset": self.onset,
            "trend": self.trend,
        }


_PAIN_SCALE_RE = re.compile(
    r"(?:đau|mức\s*độ|scale|pain|score|severity|điểm|level)\s*(?:(?:khoảng|tầm|about|around|from)\s*)?(\d+)(?:\s*(?:\/|trên|out of|over)\s*(?:10|mười))?",
    re.IGNORECASE,
)

_SEVERITY_VI = {
    r"\bdữ dội\b": "severe",
    r"\bkinh khủng\b": "severe",
    r"\bkhủng khiếp\b": "severe",
    r"\bkhông chịu nổi\b": "severe",
    r"\brất đau\b": "severe",
    r"\bđau lắm\b": "severe",
    r"\btrầm trọng\b": "severe",
    r"\bnghiêm trọng\b": "severe",
    r"\bvừa phải\b": "moderate",
    r"\bvừa\b": "moderate",
    r"\btrung bình\b": "moderate",
    r"\btương đối\b": "moderate",
    r"\bâm ỉ\b": "mild",
    r"\bnhẹ\b": "mild",
    r"\bnhẹ nhàng\b": "mild",
    r"\bhơi hơi\b": "mild",
    r"\bthoáng qua\b": "mild",
    r"\bkhông đáng kể\b": "mild",
}

_SEVERITY_EN = {
    r"\bsevere\b": "severe",
    r"\bintense\b": "severe",
    r"\bexcruciating\b": "severe",
    r"\bunbearable\b": "severe",
    r"\bworst\b": "severe",
    r"\bextreme\b": "severe",
    r"\bterrible\b": "severe",
    r"\bagonizing\b": "severe",
    r"\b10 out of 10\b": "severe",
    r"\bmoderate\b": "moderate",
    r"\bmedium\b": "moderate",
    r"\bso-so\b": "moderate",
    r"\bnoticeable\b": "moderate",
    r"\bmild\b": "mild",
    r"\bslight\b": "mild",
    r"\bminor\b": "mild",
    r"\bdull\b": "mild",
    r"\bbarely\b": "mild",
    r"\bnot bad\b": "mild",
}

_DURATION_UNITS = {
    "giây": 1 / 3600, "giay": 1 / 3600, "second": 1 / 3600, "seconds": 1 / 3600, "sec": 1 / 3600,
    "phút": 1 / 60, "phut": 1 / 60, "minute": 1 / 60, "minutes": 1 / 60, "min": 1 / 60,
    "giờ": 1, "gio": 1, "tiếng": 1, "tieng": 1, "hour": 1, "hours": 1, "hr": 1, "hrs": 1,
    "ngày": 24, "ngay": 24, "day": 24, "days": 24,
    "tuần": 168, "tuan": 168, "week": 168, "weeks": 168, "wk": 168,
    "tháng": 730, "thang": 730, "month": 730, "months": 730,
    "năm": 8760, "nam": 8760, "year": 8760, "years": 8760, "yr": 8760,
}
_DURATION_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(giờ|tiếng|ngày|tuần|tháng|năm|giây|phút|giay|tieng|ngay|tuan|thang|nam|phut|"
    r"hour|hours|day|days|week|weeks|month|months|year|years|second|seconds|minute|minutes|hr|hrs|min|sec|wk|yr)",
    re.IGNORECASE,
)
_DURATION_RANGES = re.compile(
    r"(?:khoảng|tầm|about|around|approximately|roughly|gần|hơn)\s+(\d+(?:[.,]\d+)?)\s*(giờ|tiếng|ngày|tuần|tháng|giờ|"
    r"hour|hours|day|days|week|weeks|month|months|hr|hrs)",
    re.IGNORECASE,
)
_SHORT_DURATIONS_VI = {
    r"\btừ sáng\b": 6, r"\btừ trưa\b": 4, r"\btừ chiều\b": 3,
    r"\btừ tối\b": 2, r"\btừ hôm qua\b": 24, r"\btừ hôm kia\b": 48,
    r"\bmới đây\b": 1, r"\bvừa mới\b": 0.5, r"\bvừa xong\b": 0.25,
}
_SHORT_DURATIONS_EN = {
    r"\bsince morning\b": 6, r"\bsince noon\b": 4, r"\bsince afternoon\b": 3,
    r"\bsince last night\b": 8, r"\bsince yesterday\b": 24,
    r"\bjust now\b": 0.2, r"\ba few minutes\b": 0.1, r"\ban hour ago\b": 1,
}

_ONSET_VI = {
    r"\bđột ngột\b": "sudden", r"\bbất ngờ\b": "sudden", r"\btự nhiên\b": "sudden",
    r"\bđột biến\b": "sudden", r"\bbỗng nhiên\b": "sudden",
    r"\btừ từ\b": "gradual", r"\bdần dần\b": "gradual", r"\btăng dần\b": "gradual",
    r"\bchậm rãi\b": "gradual",
}
_ONSET_EN = {
    r"\bsudden\b": "sudden", r"\bsuddenly\b": "sudden", r"\babrupt\b": "sudden",
    r"\ball of a sudden\b": "sudden", r"\bout of nowhere\b": "sudden",
    r"\bgradual\b": "gradual", r"\bgradually\b": "gradual",
    r"\bprogressive\b": "gradual", r"\bover time\b": "gradual",
    r"\bslowly\b": "gradual",
}

_TREND_VI = {
    r"\bđỡ hơn\b": "improving", r"\bđỡ\b": "improving", r"\bgiảm\b": "improving",
    r"\btốt hơn\b": "improving", r"\bthuyên giảm\b": "improving",
    r"\bnặng hơn\b": "worsening", r"\bxấu hơn\b": "worsening",
    r"\btăng lên\b": "worsening", r"\btệ hơn\b": "worsening",
    r"\btrầm trọng hơn\b": "worsening",
    r"\bkhông đổi\b": "stable", r"\bnhư cũ\b": "stable",
    r"\bkhông thay đổi\b": "stable", r"\bổn định\b": "stable",
}
_TREND_EN = {
    r"\bgetting better\b": "improving", r"\bbetter\b": "improving",
    r"\bimproving\b": "improving", r"\bless pain\b": "improving",
    r"\bsubsiding\b": "improving",
    r"\bgetting worse\b": "worsening", r"\bworse\b": "worsening",
    r"\bworsening\b": "worsening", r"\bincreasing\b": "worsening",
    r"\bdeteriorating\b": "worsening",
    r"\bsame\b": "stable", r"\bunchanged\b": "stable",
    r"\bno change\b": "stable", r"\bstable\b": "stable",
    r"\bnot different\b": "stable",
}


def _regex_match_first(text: str, patterns: dict[str, str]) -> str | None:
    text_lower = text.lower()
    for pattern, value in sorted(patterns.items(), key=lambda x: -len(x[0])):
        if re.search(pattern, text_lower):
            return value
    return None


def _parse_duration_hours(text: str) -> float | None:
    text_lower = text.lower()
    best = 0.0
    found = False

    for m in _DURATION_RE.finditer(text_lower):
        val = float(m.group(1).replace(",", "."))
        unit = m.group(2).lower()
        hours = val * _DURATION_UNITS.get(unit, 0)
        if hours > best:
            best = hours
            found = True

    for m in _DURATION_RANGES.finditer(text_lower):
        val = float(m.group(1).replace(",", "."))
        unit = m.group(2).lower()
        hours = val * _DURATION_UNITS.get(unit, 0)
        if hours > best:
            best = hours
            found = True

    if not found:
        shorthand = _SHORT_DURATIONS_VI if any(
            c for c in text if ord(c) > 127
        ) else _SHORT_DURATIONS_EN
        best_val = 0.0
        for pat, hours in shorthand.items():
            if re.search(pat, text_lower):
                if hours > best_val:
                    best_val = hours
                    found = True
        if found:
            return best_val

    return best if found else None


def _parse_pain_scale(text: str) -> int | None:
    m = _PAIN_SCALE_RE.search(text.lower())
    if m:
        val = int(m.group(1))
        if 0 <= val <= 10:
            return val
    return None


def parse_severity(text: str, language: str = "auto") -> SeverityInfo:
    if language == "auto":
        language = "vi" if any(ord(c) > 127 for c in text) else "en"

    info = SeverityInfo()

    severity_map = _SEVERITY_VI if language == "vi" else _SEVERITY_EN
    info.level = _regex_match_first(text, severity_map)

    info.pain_scale = _parse_pain_scale(text)

    info.duration_hours = _parse_duration_hours(text)

    onset_map = _ONSET_VI if language == "vi" else _ONSET_EN
    info.onset = _regex_match_first(text, onset_map)

    trend_map = _TREND_VI if language == "vi" else _TREND_EN
    info.trend = _regex_match_first(text, trend_map)

    if info.pain_scale is not None and info.level is None:
        if info.pain_scale >= 8:
            info.level = "severe"
        elif info.pain_scale >= 4:
            info.level = "moderate"
        else:
            info.level = "mild"

    return info
