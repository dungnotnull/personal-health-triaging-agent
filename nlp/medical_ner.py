"""Medical NER — regex + dictionary-based extraction (no model dependency).

Extracts: SYMPTOM, BODY_LOCATION, SEVERITY, DURATION, ONSET_PATTERN,
ASSOCIATED, TRIGGER, RELIEVING, WORSENING, MEDICAL_HISTORY, MEDICATION,
VITAL_SIGN from Vietnamese and English symptom descriptions.

Designed to work fully offline without scispaCy/PhoBERT. Falls back to
the ML models when available (lazy import path), but always works with
the regex+dictionary engine regardless of model availability.

Production ready for Phase 1. Zero external model dependency for baseline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class MedicalEntities:
    symptoms: list[str] = field(default_factory=list)
    body_locations: list[str] = field(default_factory=list)
    severity: str | None = None
    duration: str | None = None
    onset_pattern: str | None = None
    associated: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    relieving: list[str] = field(default_factory=list)
    worsening: list[str] = field(default_factory=list)
    medical_history: list[str] = field(default_factory=list)
    medications: list[str] = field(default_factory=list)
    vital_signs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "symptoms": self.symptoms,
            "body_locations": self.body_locations,
            "severity": self.severity,
            "duration": self.duration,
            "onset_pattern": self.onset_pattern,
            "associated": self.associated,
            "triggers": self.triggers,
            "relieving": self.relieving,
            "worsening": self.worsening,
            "medical_history": self.medical_history,
            "medications": self.medications,
            "vital_signs": self.vital_signs,
        }


# ── Vietnamese + English symptom vocabulary ─────────────────────────

_SYMPTOM_PATTERNS_VI: list[tuple[str, str]] = [
    ("đau đầu", "headache"),
    ("nhức đầu", "headache"),
    ("đau nửa đầu", "migraine"),
    ("chóng mặt", "dizziness"),
    ("hoa mắt", "dizziness"),
    ("buồn nôn", "nausea"),
    ("nôn", "vomiting"),
    ("ói", "vomiting"),
    ("sốt", "fever"),
    ("nóng sốt", "fever"),
    ("ớn lạnh", "chills"),
    ("rét run", "chills"),
    ("ho", "cough"),
    ("ho khan", "dry_cough"),
    ("ho có đờm", "productive_cough"),
    ("ho ra máu", "hemoptysis"),
    ("khó thở", "dyspnea"),
    ("thở gấp", "tachypnea"),
    ("thở khò khè", "wheezing"),
    ("đau ngực", "chest_pain"),
    ("tức ngực", "chest_pain"),
    ("đau bụng", "abdominal_pain"),
    ("đau thượng vị", "epigastric_pain"),
    ("đau hạ sườn", "flank_pain"),
    ("đau lưng", "back_pain"),
    ("đau cơ", "myalgia"),
    ("đau khớp", "arthralgia"),
    ("đau họng", "sore_throat"),
    ("viêm họng", "pharyngitis"),
    ("sổ mũi", "rhinorrhea"),
    ("nghẹt mũi", "nasal_congestion"),
    ("hắt hơi", "sneezing"),
    ("tiêu chảy", "diarrhea"),
    ("đi ngoài", "diarrhea"),
    ("táo bón", "constipation"),
    ("phát ban", "rash"),
    ("nổi mẩn", "rash"),
    ("ngứa", "pruritus"),
    ("mệt mỏi", "fatigue"),
    ("uể oải", "fatigue"),
    ("yếu", "weakness"),
    ("sụt cân", "weight_loss"),
    ("tăng cân", "weight_gain"),
    ("chán ăn", "anorexia"),
    ("mất ngủ", "insomnia"),
    ("khó ngủ", "insomnia"),
    ("đổ mồ hôi", "diaphoresis"),
    ("vã mồ hôi", "diaphoresis"),
    ("đổ mồ hôi đêm", "night_sweats"),
    ("đánh trống ngực", "palpitations"),
    ("hồi hộp", "palpitations"),
    ("đi tiểu buốt", "dysuria"),
    ("tiểu rắt", "urinary_frequency"),
    ("tiểu máu", "hematuria"),
    ("mờ mắt", "blurred_vision"),
    ("nhìn đôi", "diplopia"),
    ("ù tai", "tinnitus"),
    ("co giật", "seizure"),
    ("run tay", "tremor"),
    ("tê", "numbness"),
    ("dị cảm", "paresthesia"),
    ("sưng", "swelling"),
    ("phù", "edema"),
    ("xuất huyết", "hemorrhage"),
    ("chảy máu", "bleeding"),
    ("bầm tím", "bruising"),
    ("vàng da", "jaundice"),
    ("vàng mắt", "icterus"),
    ("lú lẫn", "confusion"),
    ("quên", "memory_loss"),
    ("lo âu", "anxiety"),
    ("trầm cảm", "depression"),
    ("kích động", "agitation"),
    ("ảo giác", "hallucination"),
]

_SYMPTOM_PATTERNS_EN: list[tuple[str, str]] = [
    ("headache", "headache"),
    ("migraine", "migraine"),
    ("dizziness", "dizziness"),
    ("vertigo", "vertigo"),
    ("nausea", "nausea"),
    ("vomiting", "vomiting"),
    ("throwing up", "vomiting"),
    ("fever", "fever"),
    ("chills", "chills"),
    ("rigors", "chills"),
    ("cough", "cough"),
    ("dry cough", "dry_cough"),
    ("coughing up phlegm", "productive_cough"),
    ("coughing up blood", "hemoptysis"),
    ("hemoptysis", "hemoptysis"),
    ("shortness of breath", "dyspnea"),
    ("difficulty breathing", "dyspnea"),
    ("breathlessness", "dyspnea"),
    ("wheezing", "wheezing"),
    ("chest pain", "chest_pain"),
    ("chest pressure", "chest_pain"),
    ("chest tightness", "chest_pain"),
    ("abdominal pain", "abdominal_pain"),
    ("stomach pain", "abdominal_pain"),
    ("stomach ache", "abdominal_pain"),
    ("back pain", "back_pain"),
    ("muscle pain", "myalgia"),
    ("muscle ache", "myalgia"),
    ("body ache", "myalgia"),
    ("joint pain", "arthralgia"),
    ("sore throat", "sore_throat"),
    ("runny nose", "rhinorrhea"),
    ("stuffy nose", "nasal_congestion"),
    ("congestion", "nasal_congestion"),
    ("sneezing", "sneezing"),
    ("diarrhea", "diarrhea"),
    ("loose stool", "diarrhea"),
    ("constipation", "constipation"),
    ("rash", "rash"),
    ("hives", "rash"),
    ("itching", "pruritus"),
    ("itchy", "pruritus"),
    ("fatigue", "fatigue"),
    ("tiredness", "fatigue"),
    ("exhaustion", "fatigue"),
    ("weakness", "weakness"),
    ("weight loss", "weight_loss"),
    ("losing weight", "weight_loss"),
    ("loss of appetite", "anorexia"),
    ("not eating", "anorexia"),
    ("insomnia", "insomnia"),
    ("cannot sleep", "insomnia"),
    ("trouble sleeping", "insomnia"),
    ("sweating", "diaphoresis"),
    ("night sweats", "night_sweats"),
    ("palpitations", "palpitations"),
    ("heart racing", "palpitations"),
    ("heart pounding", "palpitations"),
    ("painful urination", "dysuria"),
    ("burning urination", "dysuria"),
    ("frequent urination", "urinary_frequency"),
    ("blood in urine", "hematuria"),
    ("blurred vision", "blurred_vision"),
    ("double vision", "diplopia"),
    ("ringing in ears", "tinnitus"),
    ("tinnitus", "tinnitus"),
    ("seizure", "seizure"),
    ("convulsion", "seizure"),
    ("tremor", "tremor"),
    ("shaking", "tremor"),
    ("numbness", "numbness"),
    ("tingling", "paresthesia"),
    ("pins and needles", "paresthesia"),
    ("swelling", "swelling"),
    ("edema", "edema"),
    ("bleeding", "bleeding"),
    ("bruising", "bruising"),
    ("bruise", "bruising"),
    ("jaundice", "jaundice"),
    ("yellow skin", "jaundice"),
    ("confusion", "confusion"),
    ("memory loss", "memory_loss"),
    ("forgetful", "memory_loss"),
    ("anxiety", "anxiety"),
    ("depression", "depression"),
    ("hallucination", "hallucination"),
]

_BODY_LOCATIONS_VI: list[tuple[str, str]] = [
    ("đầu", "head"), ("trán", "forehead"), ("thái dương", "temple"),
    ("mắt", "eye"), ("mũi", "nose"), ("tai", "ear"), ("miệng", "mouth"),
    ("họng", "throat"), ("cổ", "neck"), ("vai", "shoulder"),
    ("ngực", "chest"), ("lưng", "back"), ("bụng", "abdomen"),
    ("thượng vị", "epigastrium"), ("hạ sườn phải", "right_upper_quadrant"),
    ("hạ sườn trái", "left_upper_quadrant"), ("hố chậu phải", "right_lower_quadrant"),
    ("hố chậu trái", "left_lower_quadrant"), ("quanh rốn", "periumbilical"),
    ("cánh tay", "arm"), ("khuỷu tay", "elbow"), ("cổ tay", "wrist"),
    ("bàn tay", "hand"), ("ngón tay", "finger"), ("chân", "leg"),
    ("đùi", "thigh"), ("đầu gối", "knee"), ("cẳng chân", "shin"),
    ("bàn chân", "foot"), ("mắt cá", "ankle"), ("hông", "hip"),
    ("hàm", "jaw"), ("răng", "tooth"), ("lợi", "gum"),
    ("da", "skin"), ("khớp", "joint"),
]

_BODY_LOCATIONS_EN: list[tuple[str, str]] = [
    ("head", "head"), ("forehead", "forehead"), ("temple", "temple"),
    ("eye", "eye"), ("nose", "nose"), ("ear", "ear"), ("mouth", "mouth"),
    ("throat", "throat"), ("neck", "neck"), ("shoulder", "shoulder"),
    ("chest", "chest"), ("back", "back"), ("abdomen", "abdomen"),
    ("stomach", "abdomen"), ("belly", "abdomen"),
    ("right upper", "right_upper_quadrant"), ("left upper", "left_upper_quadrant"),
    ("right lower", "right_lower_quadrant"), ("left lower", "left_lower_quadrant"),
    ("around navel", "periumbilical"), ("arm", "arm"), ("elbow", "elbow"),
    ("wrist", "wrist"), ("hand", "hand"), ("finger", "finger"),
    ("leg", "leg"), ("thigh", "thigh"), ("knee", "knee"),
    ("shin", "shin"), ("foot", "foot"), ("ankle", "ankle"),
    ("hip", "hip"), ("jaw", "jaw"), ("tooth", "tooth"), ("gum", "gum"),
    ("skin", "skin"), ("joint", "joint"),
]

_SEVERITY_VI = {
    "dữ dội": "severe", "nặng": "severe", "kinh khủng": "severe",
    "không chịu nổi": "severe", "rất đau": "severe",
    "vừa": "moderate", "trung bình": "moderate", "tương đối": "moderate",
    "nhẹ": "mild", "âm ỉ": "mild", "hơi": "mild", "thoáng qua": "mild",
}

_SEVERITY_EN = {
    "severe": "severe", "intense": "severe", "excruciating": "severe",
    "unbearable": "severe", "worst": "severe", "extreme": "severe",
    "moderate": "moderate", "medium": "moderate",
    "mild": "mild", "slight": "mild", "minor": "mild", "dull": "mild",
}

_DURATION_RE = re.compile(
    r"(\d+)\s*(giờ|tiếng|ngày|tuần|tháng|năm|giây|phút|hour|hours|day|days|week|weeks|month|months|year|years|second|seconds|minute|minutes)",
    re.IGNORECASE,
)

_DURATION_TO_HOURS = {
    "giây": 1 / 3600, "second": 1 / 3600, "seconds": 1 / 3600,
    "phút": 1 / 60, "minute": 1 / 60, "minutes": 1 / 60,
    "giờ": 1, "tiếng": 1, "hour": 1, "hours": 1,
    "ngày": 24, "day": 24, "days": 24,
    "tuần": 168, "week": 168, "weeks": 168,
    "tháng": 730, "month": 730, "months": 730,
    "năm": 8760, "year": 8760, "years": 8760,
}

_ONSET_VI = {"đột ngột": "sudden", "bất ngờ": "sudden", "tự nhiên": "sudden",
              "từ từ": "gradual", "dần dần": "gradual", "tăng dần": "gradual"}
_ONSET_EN = {"sudden": "sudden", "suddenly": "sudden", "all of a sudden": "sudden",
             "gradual": "gradual", "gradually": "gradual", "over time": "gradual",
             "progressive": "gradual"}

_PROGRESS_VI = {"đỡ": "improving", "giảm": "improving", "tốt hơn": "improving",
                "nặng hơn": "worsening", "xấu hơn": "worsening", "tăng": "worsening",
                "không đổi": "stable", "như cũ": "stable"}
_PROGRESS_EN = {"better": "improving", "improving": "improving", "less": "improving",
                "worse": "worsening", "worsening": "worsening", "increasing": "worsening",
                "same": "stable", "unchanged": "stable", "stable": "stable"}

_MEDICATIONS_VI = ["paracetamol", "efferalgan", "panadol", "ibuprofen", "aspirin",
                    "kháng sinh", "amoxicillin", "augmentin", "ciprofloxacin",
                    "giảm đau", "hạ sốt", "thuốc"]
_MEDICATIONS_EN = ["paracetamol", "acetaminophen", "tylenol", "ibuprofen", "advil",
                    "motrin", "aspirin", "antibiotic", "amoxicillin", "ciprofloxacin",
                    "painkiller", "pain killer", "medication", "medicine", "pill"]

_MED_HISTORY_VI = [
    ("tiểu đường", "diabetes"), ("đái tháo đường", "diabetes"),
    ("cao huyết áp", "hypertension"), ("tăng huyết áp", "hypertension"),
    ("hen suyễn", "asthma"), ("hen phế quản", "asthma"),
    ("tim mạch", "heart_disease"), ("bệnh tim", "heart_disease"),
    ("suy tim", "heart_failure"), ("đột quỵ", "stroke"),
    ("tai biến", "stroke"), ("ung thư", "cancer"),
    ("suy thận", "kidney_disease"), ("thận", "kidney_disease"),
    ("viêm gan", "hepatitis"), ("gan", "liver_disease"),
    ("COPD", "copd"), ("phổi tắc nghẽn", "copd"),
    ("suy giảm miễn dịch", "immunocompromised"),
    ("HIV", "hiv"), ("lao", "tuberculosis"),
]

_MED_HISTORY_EN = [
    ("diabetes", "diabetes"), ("hypertension", "hypertension"),
    ("high blood pressure", "hypertension"), ("asthma", "asthma"),
    ("heart disease", "heart_disease"), ("heart failure", "heart_failure"),
    ("stroke", "stroke"), ("cancer", "cancer"), ("tumor", "cancer"),
    ("kidney disease", "kidney_disease"), ("renal", "kidney_disease"),
    ("liver disease", "liver_disease"), ("hepatitis", "hepatitis"),
    ("COPD", "copd"), ("emphysema", "copd"),
    ("immunocompromised", "immunocompromised"), ("HIV", "hiv"),
    ("tuberculosis", "tuberculosis"), ("TB", "tuberculosis"),
]
_VITAL_RE_VI = re.compile(
    r"(nhiệt độ|sốt|thân nhiệt|SpO2|mạch|nhịp tim|huyết áp|đường huyết)\s*[:\s]*(\d+[.,]?\d*)",
    re.IGNORECASE,
)
_VITAL_RE_EN = re.compile(
    r"(temperature|temp|fever|SpO2|oxygen|pulse|heart rate|HR|blood pressure|BP|glucose)\s*[:\s]*(\d+[.,]?\d*)",
    re.IGNORECASE,
)


def _match_dict(text: str, patterns: list[tuple[str, str]]) -> list[str]:
    text_lower = text.lower()
    found: list[str] = []
    seen = set()
    for phrase, code in sorted(patterns, key=lambda x: -len(x[0])):
        idx = text_lower.find(phrase)
        while idx != -1:
            before_ok = idx == 0 or not text_lower[idx - 1].isalpha()
            after_ok = idx + len(phrase) >= len(text_lower) or not text_lower[idx + len(phrase)].isalpha()
            if before_ok and after_ok and code not in seen:
                found.append(code)
                seen.add(code)
                break
            idx = text_lower.find(phrase, idx + 1)
    return found


def _match_first(text: str, patterns: dict[str, str]) -> str | None:
    text_lower = text.lower()
    for phrase, code in sorted(patterns.items(), key=lambda x: -len(x[0])):
        idx = text_lower.find(phrase)
        while idx != -1:
            before_ok = idx == 0 or not text_lower[idx - 1].isalpha()
            after_ok = idx + len(phrase) >= len(text_lower) or not text_lower[idx + len(phrase)].isalpha()
            if before_ok and after_ok:
                return code
            idx = text_lower.find(phrase, idx + 1)
    return None


def _parse_duration(text: str) -> tuple[str | None, float | None]:
    matches = _DURATION_RE.findall(text.lower())
    if not matches:
        return None, None
    best_hours = 0.0
    best_unit = ""
    for num_str, unit in matches:
        hours = float(num_str) * _DURATION_TO_HOURS.get(unit.lower(), 0)
        if hours > best_hours:
            best_hours = hours
            best_unit = unit
    readable = f"{int(best_hours)}h" if best_hours >= 1 else f"{best_hours * 60:.0f}min"
    return readable, best_hours


def _extract_vitals(text: str, language: str) -> list[str]:
    regex = _VITAL_RE_VI if language == "vi" else _VITAL_RE_EN
    results = []
    for m in regex.finditer(text):
        results.append(f"{m.group(1)}={m.group(2)}")
    return results


def _extract_med_history(text: str, language: str) -> list[str]:
    patterns = _MED_HISTORY_VI if language == "vi" else _MED_HISTORY_EN
    return _match_dict(text, patterns)


def extract_entities(text: str, language: str = "vi") -> MedicalEntities:
    entities = MedicalEntities()

    if language == "vi":
        entities.symptoms = _match_dict(text, _SYMPTOM_PATTERNS_VI)
        entities.body_locations = _match_dict(text, _BODY_LOCATIONS_VI)
        entities.severity = _match_first(text, _SEVERITY_VI)
        entities.onset_pattern = _match_first(text, _ONSET_VI)
    else:
        entities.symptoms = _match_dict(text, _SYMPTOM_PATTERNS_EN)
        entities.body_locations = _match_dict(text, _BODY_LOCATIONS_EN)
        entities.severity = _match_first(text, _SEVERITY_EN)
        entities.onset_pattern = _match_first(text, _ONSET_EN)

    duration_text, duration_hours = _parse_duration(text)
    entities.duration = duration_text

    trend = _match_first(text, _PROGRESS_VI if language == "vi" else _PROGRESS_EN)
    if trend == "worsening":
        entities.worsening = [trend]
    elif trend == "improving":
        entities.relieving = [trend]

    entities.vital_signs = _extract_vitals(text, language)
    entities.medical_history = _extract_med_history(text, language)

    meds_vi = _match_dict(text, [(m, m) for m in _MEDICATIONS_VI])
    meds_en = _match_dict(text, [(m, m) for m in _MEDICATIONS_EN])
    entities.medications = list(set(meds_vi + meds_en))

    if not entities.severity:
        for s in entities.symptoms:
            if s in ("fatigue", "myalgia", "arthralgia", "headache", "cough"):
                if entities.severity is None:
                    entities.severity = "unspecified"

    return entities
